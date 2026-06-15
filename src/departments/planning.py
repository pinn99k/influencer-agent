"""Planning Department -- manages 4 sub-agents with context compression.

Responsibilities:
  1. Run sub-agents in dependency order
  2. Compress each result into a 3-line summary before passing to next agent
  3. Validate results against knowledge criteria
  4. Generate strategic briefing for CEO (not raw results)
"""
import json
from typing import Optional

from agents.base_agent import BaseAgent
from agents.agent_output import AgentOutput
from agents.agent_context import build_context
from agents import AGENT_CLASSES, DEPENDENCIES
from validators.output_validator import OutputValidator
from core.llm_client import call_llm, DEFAULT_PROVIDER, DEFAULT_MODEL
from core.file_manager import FileManager
from core.config import MAX_RETRY, QUALITY_THRESHOLD


_COMPRESS_SYSTEM = (
    "You are a department head summarizing an agent's analysis result.\n"
    "Produce EXACTLY 3 lines in Korean capturing the most important findings.\n"
    "These 3 lines feed the CEO strategic briefing (the next agent gets full context).\n"
    "Be specific and dense -- no generic statements. Include names, numbers, specifics.\n"
    "Output format: exactly 3 lines, no headers, no bullets, no markdown."
)

_BRIEFING_SYSTEM = (
    "You are the Planning Department head briefing the CEO.\n"
    "Given the full results of 4 sub-agents, produce a STRATEGIC BRIEFING.\n"
    "Do NOT repeat raw results. Instead:\n"
    "1. Key strategic insight (1 line)\n"
    "2. Recommended direction (1 line)\n"
    "3. Risk or uncertainty (1 line)\n"
    "4. Readiness assessment: ready for execution or needs revision (1 line)\n\n"
    "Output in Korean. Max 6 lines total. Be decisive, not descriptive."
)

_JUDGE_SYSTEM = (
    "You are a strict quality evaluator for influencer strategy documents in Korean.\n"
    "Score the output on 0-100.\n\n"
    "Criteria:\n"
    "1. Specificity (0-25): concrete names, numbers, examples. No generic filler.\n"
    "2. Accuracy (0-25): no fabricated info. Traceable to input/search data.\n"
    "3. Actionability (0-25): reader can take concrete next steps.\n"
    "4. Korean quality (0-25): complete sentences, natural flow.\n\n"
    'Output ONLY valid JSON: {\\"score\\": <int>, \\"reason\\": \\"<1-line Korean>\\"}\n'
    "Be strict. Average = 50-60. Only excellent = 80+."
)


class DepartmentResult:
    """Container for department execution results."""

    def __init__(self):
        self.agent_results: dict[str, str] = {}
        self.summaries: dict[str, str] = {}
        self.validation_results: dict[str, dict] = {}  # agent_name -> {"passed", "rules", "quality"}
        self.briefing: str = ""
        self.failed_agent: Optional[str] = None
        self.all_passed: bool = True
        # V2 (Spiral 5-A): structured agent feedback
        self.agent_questions: dict[str, list[str]] = {}   # agent_name -> questions for CEO
        self.agent_comments: dict[str, list[str]] = {}    # agent_name -> agent opinions
        self.agent_confidence: dict[str, float] = {}      # agent_name -> 0.0~1.0


class PlanningDepartment:
    """Planning Department: 4 sub-agents (subject, competition, platform, concept).

    Key behavior vs old CEO direct-call:
      - Context compression: next agent gets 3-line summary, not full prior output
      - Knowledge validation: checks output against domain knowledge criteria
      - Briefing: CEO receives strategic summary, not raw concatenation
    """

    display_name = "기획본부"

    def __init__(self, file_manager: FileManager, event_emitter=None):
        self.fm = file_manager
        self._emitter = event_emitter
        self.agents: dict[str, BaseAgent] = {
            cls.display_name: cls() for cls in AGENT_CLASSES
        }
        self._agent_order = [cls.display_name for cls in AGENT_CLASSES]

    def _emit(self, event_type: str, data: dict = None) -> None:
        if self._emitter:
            self._emitter.emit(event_type, data or {})

    def run(self, context: dict) -> DepartmentResult:
        """Execute ALL sub-agents regardless of validation results.

        Pipeline never stops mid-way. Validation results are recorded separately.
        Even if an agent fails validation, its output is passed to the next agent
        so the full pipeline always completes.
        """
        result = DepartmentResult()
        dept_context = dict(context)

        for agent_name in self._agent_order:
            agent = self.agents[agent_name]
            self._run_agent(agent_name, agent, dept_context, result)

        # Determine overall pass/fail from validation results
        failed = [n for n, v in result.validation_results.items() if not v["passed"]]
        if failed:
            result.all_passed = False
            result.failed_agent = failed[0]

        # Always generate briefing (even with failures — CEO needs to see everything)
        if result.agent_results:
            result.briefing = self._generate_briefing(result)

        return result

    def _run_agent(
        self, agent_name: str, agent: BaseAgent,
        dept_context: dict, result: DepartmentResult
    ) -> None:
        """Run one agent with retry. Always saves output and continues pipeline."""
        best_raw = None
        best_output = None
        best_val = None
        passed = False

        for attempt in range(MAX_RETRY + 1):
            self._emit("agent_start", {"agent": agent_name, "attempt": attempt + 1})
            print(f"[{self.display_name}] {agent_name} 실행 중...")
            # V2 (Spiral 5-B): agent receives only its permitted scope
            agent_input = build_context(agent_name, dept_context)
            raw = agent.run(agent_input)
            self.fm.save_raw(agent_name, raw)

            # V2 (Spiral 5-A): parse structured output once, here only
            agent_output = AgentOutput.from_raw(raw)
            content = agent_output.content

            val_result = OutputValidator.validate(
                agent_name, content, dept_context["대상자"]["이름"]
            )
            self.fm.save_validation(agent_name, val_result)

            # Keep the best attempt (first passing, or last attempt)
            if best_raw is None or val_result.passed:
                best_raw = raw
                best_output = agent_output
                best_val = val_result

            if val_result.passed:
                # Quality gate (LLM judge)
                quality = self._judge_quality(agent_name, content, dept_context)
                quality_score = quality.get("score", 100) if quality else 100
                if quality_score < QUALITY_THRESHOLD and attempt < MAX_RETRY:
                    self._emit("validation_fail", {
                        "agent": agent_name, "retry": attempt,
                        "rules": [f"품질 미달 ({quality_score}/100): {quality.get('reason', '')}"],
                    })
                    print(f"[{self.display_name}] {agent_name} 품질 미달 ({quality_score}/100), 재시도")
                    continue
                passed = True
                result.validation_results[agent_name] = {
                    "passed": True, "rules": [], "quality_score": quality_score,
                }
                break
            else:
                self._emit("validation_fail", {
                    "agent": agent_name, "retry": attempt,
                    "rules": val_result.failed_rules,
                })
                if attempt < MAX_RETRY:
                    print(f"[{self.display_name}] {agent_name} 검증 실패, 재시도 {attempt + 1}/{MAX_RETRY}")

        # If all retries exhausted without passing
        if not passed:
            print(f"[{self.display_name}] {agent_name} 검증 실패 — 산출물은 저장하고 계속 진행")
            result.validation_results[agent_name] = {
                "passed": False,
                "rules": best_val.failed_rules if best_val else [],
                "quality_score": None,
            }

        # Parsed content is the clean deliverable (no ---AGENT_OUTPUT--- block)
        content = best_output.content if best_output else (best_raw or "")

        # Always save output + pass to next agent (regardless of validation)
        dept_context[agent.context_key] = content
        result.agent_results[agent.context_key] = content

        summary = self._compress_result(agent_name, content)
        result.summaries[agent.context_key] = summary

        self.fm.save_output(agent.output_prefix, agent_name, content)

        # V2 (Spiral 5-A): structured feedback for CEO (handled in 5-B)
        if best_output:
            if best_output.questions:
                result.agent_questions[agent_name] = best_output.questions
            if best_output.comments:
                result.agent_comments[agent_name] = best_output.comments
            result.agent_confidence[agent_name] = best_output.confidence

        status = "완료" if passed else "완료 (검증 미통과)"
        self._emit("agent_done", {"agent": agent_name, "detail": summary[:200],
                                  "validated": passed})
        print(f"[{self.display_name}] {agent_name} {status}")

    def _judge_quality(self, agent_name: str, output: str, context: dict):
        """LLM-based quality evaluation. Uses Groq as judge."""
        preview = output[:1500]
        subject_info = str(context.get("대상자", {}))[:300]
        user_msg = f"Agent: {agent_name}\nSubject: {subject_info}\n\nOutput:\n{preview}"
        try:
            raw = call_llm(
                "groq", "llama-3.3-70b-versatile",
                _JUDGE_SYSTEM, user_msg, max_tokens=200,
            )
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(raw[start:end])
            return None
        except Exception as e:
            print(f"[{self.display_name}] quality judge failed ({e}), skipping")
            return None

    def _compress_result(self, agent_name: str, result: str) -> str:
        """LLM call to compress agent result into 3 dense lines."""
        preview = result[:800] if len(result) > 800 else result
        user_msg = f"Agent: {agent_name}\nResult:\n{preview}"

        try:
            compressed = call_llm(
                DEFAULT_PROVIDER, DEFAULT_MODEL,
                _COMPRESS_SYSTEM, user_msg,
                max_tokens=200,
            )
            return compressed.strip()
        except Exception as e:
            lines = [line for line in result.split("\n") if line.strip()][:3]
            return "\n".join(lines)

    def run_partial(self, context: dict, agent_names: list[str]) -> DepartmentResult:
        """지정된 에이전트만 재실행."""
        result = DepartmentResult()
        dept_context = dict(context)

        for agent_name in agent_names:
            if agent_name not in self.agents:
                print(f"[{self.display_name}] 알 수 없는 에이전트: {agent_name}, 스킵")
                continue
            agent = self.agents[agent_name]
            self._run_agent(agent_name, agent, dept_context, result)

        # 미실행 에이전트의 기존 결과 유지
        for cls in AGENT_CLASSES:
            if cls.display_name not in agent_names:
                existing = context.get(cls.context_key)
                if existing and cls.context_key not in result.agent_results:
                    result.agent_results[cls.context_key] = existing

        failed = [n for n, v in result.validation_results.items() if not v["passed"]]
        if failed:
            result.all_passed = False
            result.failed_agent = failed[0]

        if result.agent_results:
            result.briefing = self._generate_briefing(result)

        return result

    def _generate_briefing(self, result: DepartmentResult) -> str:
        """Generate strategic briefing for CEO from all completed results."""
        parts = []
        for k, v in result.summaries.items():
            parts.append(f"[{k}]\n{v}")
        summaries_text = "\n\n".join(parts)
        user_msg = f"Department results summaries:\n{summaries_text}"

        try:
            briefing = call_llm(
                DEFAULT_PROVIDER, DEFAULT_MODEL,
                _BRIEFING_SYSTEM, user_msg,
                max_tokens=300,
            )
            return briefing.strip()
        except Exception as e:
            return f"[Briefing generation failed: {e}]"
