import json

from agents import AGENT_CLASSES, get_agent_order, get_key_labels
from departments.planning import PlanningDepartment
from core.llm_client import call_llm, DEFAULT_PROVIDER, DEFAULT_MODEL
from core.file_manager import FileManager
from core.config import MAX_RETRY, CEO_REPORT_MAX_TOKENS
from core.state_manager import CEOStateManager
from core.report_builder import ReportBuilder
from core.prompt_loader import PromptLoader
from agents.manager import ManagerAgent
from agents.base_agent import _FOREIGN_CHAR_RE  # shared language-hygiene filter
from core.direction import direction_has_content
from core.directive import AgentDirective
from core.tools import WORKER_TOOLS, ToolExecutor
from core.agent_loop import AgentLoop

AGENT_ORDER = get_agent_order()

# Chairman report condition classification
# AUTO_CONDITIONS: triggered automatically by code (no LLM needed)
# LLM_CONDITIONS:  CEO judges these from content — only 3 (strategy shift) and 6 (conflict)
#   Condition 10 (quality below expectation) is intentionally excluded from auto-check:
#   it requires human judgment and is too subjective for LLM to decide reliably.
AUTO_CONDITIONS = {5, 9}
LLM_CONDITIONS = {3, 6}

# CEO LLM token budget — keep small; CEO calls are judgment, not generation
CEO_MAX_TOKENS = 1000

_CEO_SUMMARY_SYSTEM = """\
You are the CEO of an influencer management agency.
Given the subject's basic info (and, during reanalysis, the user's feedback
and/or performance data), write a SHORT strategic direction that sub-agents
(subject/competition/platform/concept analysts) read before their work.

If user feedback or performance data is provided, you MUST carry the user's
specific requests forward as concrete directives. Do NOT generalize them away
— keep specifics like "switch concept A->B" or "focus on YouTube shorts"
explicit so the analysts actually change their output accordingly.

Write 2-4 sentences in Korean. Be concrete and directional:
- the core strength to exploit
- the platform/content direction (adjusted by feedback/performance if given)
- one thing analysts should pay attention to

Output ONLY the Korean paragraph. No headers, no JSON, no preamble.
"""

_REANALYZE_JUDGE_SYSTEM = """\
You are the CEO of an influencer management agency.
Given the user's feedback and/or performance data, decide which agents need to be re-run.

Available agents (in order):
1. 대상분석 - subject strengths/weaknesses/differentiator
2. 경쟁분석 - competition analysis, market gaps
3. 플랫폼추천 - platform recommendation
4. 컨셉기획 - concept planning, calendar, filming guide

DEPENDENCY RULES:
- If 대상분석 re-runs → 경쟁분석, 플랫폼추천, 컨셉기획 must also re-run
- If 경쟁분석 re-runs → 플랫폼추천, 컨셉기획 must also re-run
- If 플랫폼추천 re-runs → 컨셉기획 must also re-run
- 컨셉기획 can re-run alone

Respond with ONLY valid JSON — no markdown fences:
{"rerun_agents": ["에이전트명", ...], "reason": "<1-line Korean>"}

Be conservative — only re-run what's strictly needed.
"""

# Inline quality-judge prompt (English only — no Korean text rule applies to files,
# not to in-memory string constants, but we keep it English for consistency)
_QUALITY_JUDGE_SYSTEM = """\
You are a quality evaluator for an influencer analysis system.
Given the agent name, its output, and the subject's goal, judge if the output meets quality standards.

Quality standards:
- Output is specific to the subject (not generic advice)
- All required sections are present and non-empty
- Findings are concrete, not vague
- No obvious hallucinations or contradictions

Respond with ONLY valid JSON — no markdown fences, no extra text:
{"passed": <true|false>, "reason": "<one-sentence reason>", "summary_for_next": "<3 lines max capturing key findings>"}

The summary_for_next field will be shown to the next agent as context, so make it dense and useful.
"""

# Inline chairman-condition check prompt (conditions 3 and 6 only)
# Condition 10 is excluded — it requires human judgment, not LLM auto-detection.
_CHAIRMAN_CHECK_SYSTEM = """\
You are the CEO of an influencer management agency reviewing an agent's output.
Check ONLY these two chairman report conditions:
  3. Strategy direction change needed (initial goal, platform, or target age group MUST change based on evidence)
  6. Conflicting results between agents (direct factual contradictions that cannot be reconciled)

Trigger ONLY when the evidence is clear and unambiguous.
When in doubt, do NOT trigger — the default should always be to continue.

Respond with ONLY valid JSON — no markdown fences, no extra text:
{"triggered": <true|false>, "condition": <3|6|0>, "reason": "<one-sentence reason>"}

If no condition is triggered, return {"triggered": false, "condition": 0, "reason": "ok"}.
"""


class CEO:
    """Orchestration only. SRP: agent call sequence, judgment, flow control.
    State management -> CEOStateManager
    Document generation -> ReportBuilder
    Prompt loading -> PromptLoader

    LLM judgment points (Spiral 1+):
      1. _interpret_goal  — LLM reads subject info → produces plan.md
      2. _decide_next     — LLM reads current state → decides next action (JSON)
      3. _judge_quality   — LLM reads agent output → pass/fail + compressed summary
      4. _check_llm_chairman_conditions — LLM checks conditions 3, 6, 10
    """

    def __init__(self, file_manager: FileManager, dry_run: bool = False, event_emitter=None):
        self.fm = file_manager
        self.dry_run = dry_run
        self._emitter = event_emitter
        self._state_mgr = CEOStateManager(file_manager)
        self._reports = ReportBuilder(file_manager)
        self._prompts = PromptLoader()
        self._planning_dept = PlanningDepartment(file_manager, event_emitter=event_emitter)
        self._manager = ManagerAgent(file_manager, event_emitter=event_emitter)
        # Backward compat: expose agents dict for tests/external refs
        self.agents = self._planning_dept.agents
        self._summaries: dict[str, str] = {}
        # Last reanalyze decision rationale (surfaced to the web UI, Fix E)
        self._last_rerun_reason: str = ""

    # -- backward compat properties (tests, external refs) --

    @property
    def state(self) -> dict:
        return self._state_mgr.state

    @state.setter
    def state(self, value: dict) -> None:
        self._state_mgr.state = value

    # -- event emission --

    def _emit(self, event_type: str, data: dict = None) -> None:
        if self._emitter:
            self._emitter.emit(event_type, data or {})

    def _emit_fallback(self, method: str, error: Exception) -> None:
        """Track 0 runtime visibility: judgments still fall back silently for
        operational safety, but the degradation is now observable — the UI/logs
        can show that a judgment ran on its fallback instead of real LLM output."""
        self._emit("judgment_fallback", {"method": method, "error": str(error)[:200]})

    # -- public API --

    def _load_reanalyze_inputs(self, context: dict) -> None:
        """재분석 입력 일괄 로드: 기존 산출물 + 성과기록 + 피드백 + 방향.

        모든 디스크 입력이 이 한 곳을 거친다 — 재분석이 무엇을 보는지 추적할 때
        여기만 보면 된다."""
        existing = self.fm.load_existing_outputs()
        for key, value in existing.items():
            if value and not context.get(key):
                context[key] = value
        perf = self.fm.load_performance_record()
        if perf:
            context["성과_기록"] = perf
        feedback = self.fm.load_feedback()
        if feedback:
            context["피드백"] = feedback
        self._load_direction(context)

    def _load_direction(self, context: dict) -> None:
        """사용자가 정한 방향(방향.md)을 컨텍스트에 주입. 없으면 무변화.

        방향은 _build_ceo_summary 를 통해 ceo_summary 에 실려 에이전트까지 전달된다
        (피드백과 동일 경로 재사용)."""
        direction = self.fm.load_direction()
        if direction and direction_has_content(direction):
            context["방향"] = direction

    def run(self, context: dict) -> None:
        # 성과기록이 있으면 자동 주입
        perf = self.fm.load_performance_record()
        if perf:
            context["성과_기록"] = perf
        self._load_direction(context)
        self._interpret_goal(context)
        self._agent_loop(context)
        if not self.dry_run:
            if self._state_mgr.current_phase == "회장보고대기":
                print("[CEO] 회장 보고 대기 중 — 최종화 건너뜀")
                return
            self._finalize(context)

    def run_autonomous(self, context: dict) -> dict:
        """Phase 2 (Phase C): 고정 파이프라인 대신 도구 호출 루프로 분석한다.

        CEO가 도구(워커)를 스스로 골라 호출하고 결과를 보고 다음을 정한다. 1장의
        워커/검증/저장을 그대로 재사용(run_partial). 정지: finish / max_iter.
        """
        self._state_mgr.init_state(context["대상자"]["이름"])
        self._state_mgr.update("current_phase", "자율루프")
        if self.dry_run:
            return {"iterations": 0, "finished": False, "ran": [], "messages": []}

        # run() 과 동일하게 성과·방향을 주입한다(자율 모드도 사용자 방향을 반영해야 함).
        perf = self.fm.load_performance_record()
        if perf:
            context["성과_기록"] = perf
        self._load_direction(context)
        self._build_ceo_summary(context)
        system = self._prompts.load_prompt("ceo/autonomous")
        subject_json = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        goal = context["대상자"].get("목표", "")
        user_msg = chr(10).join([
            "대상자 정보:",
            subject_json,
            "",
            "목표: " + goal,
            "",
            "도구를 사용해 분석을 진행하고, 모두 끝나면 finish를 호출하세요.",
        ])

        from core.measure import MeasureStore
        executor = ToolExecutor(
            context, self._planning_dept,
            event_emitter=self._emitter, measure_store=MeasureStore(self.fm.name),
        )
        loop = AgentLoop(
            executor, WORKER_TOOLS, system,
            provider="openai", model="gpt-4o", max_iter=8,
            event_emitter=self._emitter,
        )
        self._emit("pipeline_started")
        loop_result = loop.run(user_msg)
        for agent_name in executor.ran:
            self._state_mgr.update_agent(agent_name, "DONE")
        self._emit("pipeline_completed", {
            "ran": loop_result["ran"], "iterations": loop_result["iterations"],
            "stop_reason": loop_result.get("stop_reason"),
        })
        self._finalize(context)
        return loop_result

    # ──────────────────────────────────────────────
    # Phase 1: Goal interpretation (LLM #1)
    # ──────────────────────────────────────────────

    def _interpret_goal(self, context: dict) -> None:
        self._state_mgr.init_state(context["대상자"]["이름"])

        if self.dry_run:
            system_prompt = self._prompts.load_prompt("ceo/goal_interpretation")
            self.fm.save_prompt_output("ceo_goal_interpretation", system_prompt)
            self._state_mgr.update("current_phase", "dry_run_완료")
            print("[dry_run] CEO goal interpretation prompt saved")
            return

        system_prompt = self._prompts.load_prompt("ceo/goal_interpretation")
        knowledge = self._prompts.load_knowledge_for("전략수립")
        if knowledge:
            system_prompt = system_prompt + "\n\n# DOMAIN KNOWLEDGE\n" + knowledge

        subject_json = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        user_msg = f"Subject information:\n{subject_json}"

        try:
            plan = call_llm(
                DEFAULT_PROVIDER,
                DEFAULT_MODEL,
                system_prompt,
                user_msg,
                max_tokens=CEO_MAX_TOKENS,
            )
        except Exception as e:
            # Fallback to minimal plan so the loop can still run
            self._emit_fallback("_interpret_goal", e)
            name = context["대상자"]["이름"]
            plan = (
                f"# CEO Execution Plan\n"
                f"Subject: {name}\n"
                f"Order: subject_analysis -> competition_analysis -> platform_recommendation -> concept_planning\n"
                f"[LLM call failed: {e}]"
            )

        plan = _FOREIGN_CHAR_RE.sub("", plan)
        context["에이전트_지시"] = self._parse_agent_instructions(plan)
        self.fm.save_plan(plan)
        self._emit("plan_created", {"subject": context["대상자"]["이름"]})
        self._state_mgr.update("current_phase", "실행중")
        # Store goal summary for use in _decide_next
        self._state_mgr.update("goal_summary", context["대상자"].get("목표", ""))

    @staticmethod
    def _parse_agent_instructions(plan: str) -> dict:
        """Recover each agent's instruction from the plan table so it reaches the
        worker (previously it lived only in plan.md). Best-effort; skips garbled rows.

        goal_interpretation emits '| 순서 | 에이전트 | 핵심 지시 |'.
        """
        result = {}
        for line in (plan or "").splitlines():
            if "|" not in line:
                continue
            cells = [c.strip() for c in line.split("|")]
            for i, c in enumerate(cells):
                if c in AGENT_ORDER and i + 1 < len(cells):
                    instr = cells[i + 1].strip()
                    if instr and instr not in ("핵심 지시", "지시"):
                        result[c] = instr
        return result

    # ──────────────────────────────────────────────
    # Phase 2: Agent loop
    # ──────────────────────────────────────────────

    def _handle_agent_questions(self, context: dict) -> None:
        """V2 (Spiral 5-B): 에이전트 질문을 3단계로 분류·처리.

        STRATEGIC -> 회장 에스컬레이션 / TACTICAL -> CEO 답변 /
        DATA -> 컨텍스트에서 답하거나 회장에게 데이터 요청.
        결과는 context['질문_응답']에 저장(최종 리포트·후속 처리용).
        """
        qmap = context.get("에이전트_질문", {}) or {}
        pairs = [(a, q) for a, qs in qmap.items() for q in (qs or [])]
        result = {"answers": {}, "escalated": [], "data_requests": []}
        if not pairs or self.dry_run:
            context["질문_응답"] = result
            return

        subject = json.dumps(context.get("대상자", {}), ensure_ascii=False)
        qlist = "\n".join(f"- [{a}] {q}" for a, q in pairs)
        user_msg = f"대상자 정보:\n{subject}\n\n에이전트 질문:\n{qlist}"
        try:
            system = self._prompts.load_prompt("ceo/question_handler")
            raw = call_llm(
                DEFAULT_PROVIDER, DEFAULT_MODEL, system, user_msg,
                max_tokens=CEO_MAX_TOKENS,
            ).strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            for c in data.get("classifications", []):
                q = c.get("question", "")
                qtype = (c.get("type") or "TACTICAL").upper()
                ans = c.get("answer")
                if qtype == "STRATEGIC":
                    result["escalated"].append(q)
                elif qtype == "DATA":
                    if ans:
                        result["answers"][q] = ans
                    else:
                        result["data_requests"].append(q)
                else:
                    result["answers"][q] = ans or "(CEO 판단 보류)"
        except Exception as e:
            print(f"[CEO._handle_agent_questions] 분류 실패 ({e}), 전체 에스컬레이션")
            self._emit_fallback("_handle_agent_questions", e)
            result["escalated"] = [q for _, q in pairs]

        context["질문_응답"] = result
        n_esc, n_data = len(result["escalated"]), len(result["data_requests"])
        if n_esc or n_data:
            self._emit("agent_questions_pending",
                       {"escalated": n_esc, "data_requests": n_data})
            print(f"[CEO] 에이전트 질문 처리 — 답변 {len(result['answers'])}건, "
                  f"에스컬레이션 {n_esc}건, 데이터요청 {n_data}건")

    def _build_ceo_summary(self, context: dict) -> None:
        """V2 (Spiral 5-B): 1-paragraph strategic direction for sub-agents.

        Stored in context['ceo_summary']; AgentContext passes it to scoped agents.
        """
        if self.dry_run:
            context["ceo_summary"] = ""
            return
        subject = json.dumps(context.get("대상자", {}), ensure_ascii=False, indent=2)
        direction = (context.get("방향") or "").strip()
        feedback = (context.get("피드백") or "").strip()
        performance = (context.get("성과_기록") or "").strip()

        user_msg = f"대상자 정보:\n{subject}\n"
        if direction:
            user_msg += f"\n사용자가 정한 방향(최우선 반영):\n{direction}\n"
        if feedback:
            user_msg += f"\n사용자 피드백(반드시 반영):\n{feedback}\n"
        if performance:
            user_msg += f"\n성과 데이터:\n{performance[:500]}\n"

        try:
            summary = call_llm(
                DEFAULT_PROVIDER, DEFAULT_MODEL,
                _CEO_SUMMARY_SYSTEM, user_msg,
                max_tokens=CEO_MAX_TOKENS,
            ).strip()
        except Exception as e:
            print(f"[CEO._build_ceo_summary] LLM 실패 ({e}), 요약 생략")
            self._emit_fallback("_build_ceo_summary", e)
            summary = ""
        summary = _FOREIGN_CHAR_RE.sub("", summary)

        # Phase A: build a STRUCTURED per-agent directive. Each agent gets the CEO
        # strategy + ITS specific instruction (parsed from the plan, previously
        # orphaned on disk) + the user's direction/feedback. In Phase 2 this
        # directive is the tool-call payload.
        instructions = context.get("에이전트_지시", {}) or {}
        context["directives"] = {
            name: AgentDirective(
                strategy=summary,
                instruction=instructions.get(name, ""),
                direction_md=direction,
                feedback=feedback,
                performance=performance,
            ).to_prompt_text()
            for name in AGENT_ORDER
        }

        # Backward-compatible general fallback (agents without a directive, e.g.
        # reanalysis). Direction + feedback appended verbatim as before.
        if direction:
            summary = (summary + "\n\n" + direction).strip()
        if feedback:
            summary = (summary + "\n\n[사용자 피드백 — 반드시 반영]\n" + feedback).strip()

        context["ceo_summary"] = summary
        if summary:
            print(f"[CEO] 전략 요약 생성:\n{summary}\n")

    def _agent_loop(self, context: dict) -> None:
        if self.dry_run:
            for name in AGENT_ORDER:
                agent = self.agents[name]
                self.fm.save_prompt_output(name, agent.system_prompt)
                print(f"[dry_run] {name} prompt saved")
            return

        # V2 (Spiral 5-B): strategic summary for sub-agents (AgentContext)
        self._build_ceo_summary(context)

        # Delegate to PlanningDepartment
        self._emit("pipeline_started")
        dept_result = self._planning_dept.run(context)

        # Propagate results to main context for finalize/report
        for key, value in dept_result.agent_results.items():
            context[key] = value
        self._summaries = dept_result.summaries

        # Update state for each completed agent
        for agent_name in AGENT_ORDER:
            agent = self.agents[agent_name]
            if agent.context_key in dept_result.agent_results:
                self._state_mgr.update_agent(agent_name, "DONE")

        # Store validation results in context for reports
        context["검증_결과"] = dept_result.validation_results

        # V2 (Spiral 5-A): structured agent feedback (handling in 5-B)
        context["에이전트_질문"] = dept_result.agent_questions
        context["에이전트_의견"] = dept_result.agent_comments
        context["에이전트_신뢰도"] = dept_result.agent_confidence

        if not dept_result.all_passed:
            failed = [n for n, v in dept_result.validation_results.items() if not v["passed"]]
            self._emit("pipeline_completed_with_issues", {
                "failed_agents": failed,
                "total": len(AGENT_ORDER),
                "passed": len(AGENT_ORDER) - len(failed),
            })
            print(f"[CEO] 파이프라인 완료 — 검증 실패 에이전트: {failed}")

        # CEO reviews department briefing for chairman conditions
        if dept_result.briefing:
            print(f"\n[CEO] Department briefing:\n{dept_result.briefing}\n")
            self._check_briefing_for_chairman(dept_result.briefing, context)

        # V2 (Spiral 5-B): 에이전트 질문 3단계 처리
        self._handle_agent_questions(context)

        self._emit("pipeline_completed")
        self._update_plan(AGENT_ORDER[-1], context)

    # ──────────────────────────────────────────────
    # Phase 3: Finalize
    # ──────────────────────────────────────────────

    def _notify_manager_completion(self, context: dict, final_report: str) -> None:
        """V2 (Spiral 5-D): 매니저가 완료 요약 + 1주차 카드 + 성과요청 발송 (비핵심 경로)."""
        try:
            self._manager.generate_completion_summary(final_report)
            calendar = context.get("컨셉_기획", "")
            if calendar:
                self._manager.generate_weekly_card(calendar, 1)
                self._manager.request_performance_input(1)
        except Exception as e:
            print(f"[CEO] 매니저 알림 실패 ({e})")

    def _finalize(self, context: dict) -> None:
        self._emit("finalize_started")
        self._request_approval(context)
        final_report = self._synthesize_final_report(context)
        self.fm.save_final_report(final_report)
        self._notify_manager_completion(context, final_report)
        self._state_mgr.update("current_phase", "완료")
        self.fm.save_snapshot()
        self._generate_handover(context)

    def _synthesize_final_report(self, context: dict) -> str:
        """Generate an executive strategy report; fall back to concatenation on failure."""
        payload = {
            "대상자": context.get("대상자", {}),
            "대상_분석": context.get("대상_분석", ""),
            "경쟁_분석": context.get("경쟁_분석", ""),
            "플랫폼_추천": context.get("플랫폼_추천", ""),
            "컨셉_기획": context.get("컨셉_기획", ""),
            "성과_기록": context.get("성과_기록", ""),
            "방향": context.get("방향", ""),
        }
        try:
            system = self._prompts.load_prompt("ceo/final_report")
            subject_name = str(payload.get("대상자", {}).get("이름", "")).strip()
            required = (
                "## 한 줄 결론",
                "## 핵심 결정 3가지",
                "## 강점과 기회",
                "## 4주 실행 로드맵",
                "## 지금 당장 할 3가지",
                "## 성공 지표",
                "## 매주 반복 루틴",
                "## 성과 기록",
                "## 2주 후 셀프 점검",
            )

            def _attempt(extra: str = "") -> str:
                raw = call_llm(
                    "openai",
                    "gpt-4o",
                    system + extra,
                    json.dumps(payload, ensure_ascii=False, indent=2),
                    max_tokens=CEO_REPORT_MAX_TOKENS,
                )
                return _FOREIGN_CHAR_RE.sub("", raw).strip()

            def _ok(t: str) -> bool:
                sections_ok = all(s in t for s in required)
                name_ok = (not subject_name) or (subject_name in t)
                return sections_ok and name_ok

            text = _attempt()
            if not _ok(text):
                # 이름이 틀리거나 섹션이 빠지면 한 번 더 강하게 지시해 재생성한다.
                text = _attempt(
                    f"\n\n[필수] 대상자 이름은 정확히 '{subject_name}' 이다. "
                    f"한 글자도 바꾸지 말고 그대로 쓴다. 위 6개 섹션 헤더를 모두 포함한다."
                )
            if _ok(text):
                return text
            raise ValueError("final report failed section/name gate")
        except Exception as e:
            print(f"[CEO._synthesize_final_report] 실패 ({e}) -> 폴백")
            self._emit_fallback("_synthesize_final_report", e)
        return self._reports.build_final_report(context, get_key_labels())

    # ──────────────────────────────────────────────
    # LLM judgment methods
    # ──────────────────────────────────────────────

    def _check_briefing_for_chairman(self, briefing: str, context: dict) -> None:
        """CEO reviews department briefing for chairman report conditions 3 and 6."""
        user_msg = (
            f"Department briefing:\n{briefing}\n\n"
            f"Subject goal: {context.get('대상자', {}).get('목표', '')}"
        )
        try:
            raw = call_llm(
                DEFAULT_PROVIDER, DEFAULT_MODEL,
                _CHAIRMAN_CHECK_SYSTEM, user_msg,
                max_tokens=CEO_MAX_TOKENS,
            )
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            check = json.loads(raw.strip())
            if check.get("triggered"):
                condition_no = check.get("condition", 0)
                if condition_no in LLM_CONDITIONS:
                    self._report_to_chairman(condition_no, context)
        except Exception as e:
            print(f"[CEO._check_briefing_for_chairman] LLM check failed ({e}), skipping")

    def _decide_next(self, context: dict) -> dict:
        """LLM decides next action based on current state.

        Returns dict: {"action": "run|rework|complete|chairman_report",
                        "target": str, "reason": str, "condition": int}
        Falls back to sequential if LLM call fails or returns invalid JSON.
        """
        completed = [n for n in AGENT_ORDER if context.get(self.agents[n].context_key)]
        remaining = [n for n in AGENT_ORDER if n not in completed]

        if not remaining:
            return {"action": "complete", "target": "", "reason": "all agents done", "condition": 0}

        system_prompt = self._prompts.load_prompt("ceo/next_decision")

        # Build compressed context summary for the LLM (token-efficient)
        last_summary = ""
        if completed:
            last_agent = completed[-1]
            last_key = self.agents[last_agent].context_key
            last_summary = self._summaries.get(last_key, "")
            if not last_summary and context.get(last_key):
                last_summary = context[last_key][:300]

        decision_input = {
            "completed_agents": completed,
            "remaining_agents": remaining,
            "subject_goal": context.get("대상자", {}).get("목표", ""),
            "last_result_summary": last_summary,
        }
        user_msg = json.dumps(decision_input, ensure_ascii=False, indent=2)

        try:
            raw = call_llm(
                DEFAULT_PROVIDER,
                DEFAULT_MODEL,
                system_prompt,
                user_msg,
                max_tokens=CEO_MAX_TOKENS,
            )
            # Strip markdown fences if present
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            action = json.loads(raw.strip())
            # Validate required keys
            if "action" not in action:
                raise ValueError("missing 'action' key")
            # Ensure target is a known agent when action is run/rework
            if action["action"] in ("run", "rework") and action.get("target") not in self.agents:
                action["target"] = remaining[0]
            return action
        except Exception as e:
            print(f"[CEO._decide_next] LLM parse failed ({e}), falling back to sequential")
            self._emit_fallback("_decide_next", e)
            return {"action": "run", "target": remaining[0], "reason": "sequential fallback", "condition": 0}

    def _judge_quality(self, agent_name: str, result: str, context: dict) -> dict:
        """LLM quality judgment — Stage 2 after structural validator passes.

        Returns dict: {"passed": bool, "reason": str, "summary_for_next": str}
        Falls back to {"passed": True, ...} if LLM call fails.
        """
        subject_goal = context.get("대상자", {}).get("목표", "")
        # Truncate result to keep CEO token cost low
        result_preview = result[:3000] if len(result) > 3000 else result

        user_msg = (
            f"Agent: {agent_name}\n"
            f"Subject goal: {subject_goal}\n\n"
            f"Agent output (first 3000 chars):\n{result_preview}"
        )

        try:
            raw = call_llm(
                DEFAULT_PROVIDER,
                DEFAULT_MODEL,
                _QUALITY_JUDGE_SYSTEM,
                user_msg,
                max_tokens=CEO_MAX_TOKENS,
            )
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            judgment = json.loads(raw.strip())
            if "passed" not in judgment:
                raise ValueError("missing 'passed' key")
            return judgment
        except Exception as e:
            print(f"[CEO._judge_quality] LLM parse failed ({e}), defaulting to pass")
            self._emit_fallback("_judge_quality", e)
            return {
                "passed": True,
                "reason": f"LLM unavailable ({e}), auto-pass",
                "summary_for_next": result[:300],
            }

    def _check_llm_chairman_conditions(self, agent_name: str, result: str, context: dict) -> None:
        """Check chairman report conditions 3, 6, 10 via LLM after each agent completes.

        Conditions checked:
          3 — strategy direction change needed
          6 — conflicting results between agents
          10 — result far below expected quality
        """
        completed = [n for n in AGENT_ORDER if context.get(self.agents[n].context_key)]
        # Only meaningful with 2+ completed agents for condition 6;
        # conditions 3 and 10 apply from the first agent onward.

        result_preview = result[:3000] if len(result) > 3000 else result
        prior_summaries = {
            n: self._summaries.get(self.agents[n].context_key, "")
            for n in completed if n != agent_name
        }

        user_msg = (
            f"Current agent: {agent_name}\n"
            f"Subject goal: {context.get('대상자', {}).get('목표', '')}\n\n"
            f"Current agent output (first 3000 chars):\n{result_preview}\n\n"
            f"Prior agent summaries:\n"
            + "\n".join(f"  {k}: {v[:200]}" for k, v in prior_summaries.items())
        )

        try:
            raw = call_llm(
                DEFAULT_PROVIDER,
                DEFAULT_MODEL,
                _CHAIRMAN_CHECK_SYSTEM,
                user_msg,
                max_tokens=CEO_MAX_TOKENS,
            )
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            check = json.loads(raw.strip())
            if check.get("triggered"):
                condition_no = check.get("condition", 0)
                if condition_no in LLM_CONDITIONS:
                    self._report_to_chairman(condition_no, context)
        except Exception as e:
            # Non-fatal: if check fails, continue without triggering chairman report
            print(f"[CEO._check_llm_chairman_conditions] LLM check failed ({e}), skipping")

    def _request_approval(self, context: dict) -> None:
        """Chairman report condition 9: all outputs ready, about to hand off to execution.
        Saves a briefing and prints it; does NOT block (CLI flow handles the pause)."""
        self._report_to_chairman(9, context)

    # ──────────────────────────────────────────────
    # Chairman report
    # ──────────────────────────────────────────────

    def _report_to_chairman(self, condition_no: int, context: dict) -> None:
        self._state_mgr.update("current_phase", "회장보고대기")
        context["보고_조건"] = {
            "조건번호": condition_no,
            "근거": f"조건 {condition_no}번 해당",
            "조치": "즉시중단",
        }
        briefing = self._reports.build_briefing(
            condition_no, context, self._state_mgr.state
        )
        self.fm.save_briefing(condition_no, briefing)
        print(briefing)
        if self._emitter and hasattr(self._emitter, 'wait_for_decision') and condition_no != 9:
            self._emit("briefing_pending", {"condition": condition_no, "briefing": briefing})
            decision = self._emitter.wait_for_decision()
            if decision:
                context["회장_결정"] = decision
                self._emit("decision_received", {
                    "condition": condition_no, "choice": decision.get("choice", ""),
                })

    # ──────────────────────────────────────────────
    # Plan update helpers
    # ──────────────────────────────────────────────

    def _update_plan(self, completed_agent: str, context: dict) -> None:
        completed = [n for n in AGENT_ORDER if context.get(self.agents[n].context_key)]
        remaining = [n for n in AGENT_ORDER if n not in completed]
        progress = self._reports.build_plan(completed, remaining)
        # Save to progress.md — do NOT overwrite the strategic plan.md
        # generated by _interpret_goal (that LLM strategy must be preserved).
        self.fm.save_progress(progress)

    def _generate_handover(self, context: dict) -> None:
        completed = [n for n in AGENT_ORDER if context.get(self.agents[n].context_key)]
        content = self._reports.build_handover(context, AGENT_ORDER, completed)
        self.fm.save_handover(content)

    # ──────────────────────────────────────────────
    # Reanalyze mode
    # ──────────────────────────────────────────────

    def run_reanalyze(self, context: dict) -> None:
        """재분석 모드: 기존 산출물 + 성과기록 + 피드백 기반 부분 재실행."""
        self._state_mgr.init_state(context["대상자"]["이름"])
        self._state_mgr.update("current_phase", "재분석중")
        self._load_reanalyze_inputs(context)

        # CEO LLM 판단: 어떤 에이전트 재실행?
        rerun_agents = self._decide_rerun(context)
        # Surface the decision (agents + rationale) to the web UI so the user can
        # see *what* CEO chose to rerun and *why*, then correct it (Fix E).
        self._emit("rerun_decided", {
            "rerun_agents": rerun_agents,
            "reason": self._last_rerun_reason,
        })
        # Provenance: record this as an AI decision in the measure layer so the
        # portfolio can honestly separate AI vs human judgments. Measurement must
        # never break the pipeline -> swallow errors.
        try:
            from core.measure import MeasureStore, DecisionEntry, ACTOR_AI
            basis_parts = []
            if context.get("피드백"):
                basis_parts.append("피드백")
            if context.get("성과_기록"):
                basis_parts.append("성과기록")
            MeasureStore(self.fm.name).log_decision(DecisionEntry(
                actor=ACTOR_AI,
                basis=("+".join(basis_parts) or "입력 없음") + " 기반 재분석 판단",
                decision=f"재실행: {', '.join(rerun_agents) or '없음'} — {self._last_rerun_reason}",
            ))
        except Exception as e:
            print(f"[CEO] 측정 로그 실패 ({e})")
        if not rerun_agents:
            self._emit("reanalyze_skipped", {"reason": self._last_rerun_reason})
            print(f"[CEO] 재실행 안 함 — {self._last_rerun_reason}")
            return

        print(f"[CEO] 재실행 대상: {' → '.join(rerun_agents)}")

        # 부분 재실행
        self._build_ceo_summary(context)
        self._emit("pipeline_started")
        dept_result = self._planning_dept.run_partial(context, rerun_agents)

        for key, value in dept_result.agent_results.items():
            context[key] = value
        self._summaries.update(dept_result.summaries)

        for agent_name in rerun_agents:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                if agent.context_key in dept_result.agent_results:
                    self._state_mgr.update_agent(agent_name, "DONE")

        context["검증_결과"] = dept_result.validation_results
        context["에이전트_질문"] = dept_result.agent_questions
        context["에이전트_의견"] = dept_result.agent_comments
        context["에이전트_신뢰도"] = dept_result.agent_confidence
        try:
            self._manager.generate_progress_report(dept_result.agent_results, dept_result.validation_results)
        except Exception as e:
            print(f"[CEO] 매니저 진행보고 실패 ({e})")
        self._emit("pipeline_completed")

        # 최종화
        if not self.dry_run:
            self._finalize(context)

    def _decide_rerun(self, context: dict) -> list[str]:
        """LLM이 피드백/성과 기반으로 재실행 대상 결정."""
        feedback = context.get("피드백", "")
        performance = context.get("성과_기록", "")
        direction = context.get("방향", "")

        # 새 입력(성과/피드백/방향)이 전혀 없으면 재분석할 근거가 없다 -> 재실행 안 함.
        # run_reanalyze 가 빈 리스트를 받으면 안전하게 멈추고 skip 이벤트를 낸다.
        if not feedback and not performance and not direction:
            self._last_rerun_reason = "재분석 입력 없음(성과·피드백·방향 모두 비어 있음) — 재실행 안 함"
            return []

        user_msg = ""
        if feedback:
            user_msg += f"User feedback:\n{feedback}\n\n"
        if performance:
            user_msg += f"Performance data:\n{performance[:500]}\n\n"
        if direction:
            user_msg += f"User-set strategic direction:\n{direction[:500]}\n\n"
        for agent_name in AGENT_ORDER:
            agent = self.agents[agent_name]
            output = context.get(agent.context_key, "")
            if output:
                user_msg += f"Current {agent_name} output (first 200 chars):\n{output[:200]}\n\n"

        try:
            raw = call_llm(
                DEFAULT_PROVIDER, DEFAULT_MODEL,
                _REANALYZE_JUDGE_SYSTEM, user_msg,
                max_tokens=CEO_MAX_TOKENS,
            )
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            decision = json.loads(raw.strip())
            agents = decision.get("rerun_agents", [])
            reason = decision.get("reason", "")
            self._last_rerun_reason = reason or "재분석 대상 선정 완료"
            print(f"[CEO] 재분석 판단: {reason}")
            ordered = [n for n in AGENT_ORDER if n in agents]
            return ordered
        except Exception as e:
            self._last_rerun_reason = "판단 실패 — 안전하게 전체 재분석"
            print(f"[CEO._decide_rerun] LLM 실패 ({e}), 전체 재실행")
            self._emit_fallback("_decide_rerun", e)
            return list(AGENT_ORDER)

    # ──────────────────────────────────────────────
    # Backward compat (tests reference these)
    # ──────────────────────────────────────────────

    def _init_state(self, subject_name: str) -> None:
        self._state_mgr.init_state(subject_name)

    def _update_state(self, key: str, value) -> None:
        self._state_mgr.update(key, value)
