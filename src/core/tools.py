"""core/tools.py -- 도구 정의 + 실행기 (Phase 2 / Phase C).

WORKER_TOOLS: CEO 자율 루프가 호출하는 OpenAI 함수 스키마(워커 4 + finish).
ToolExecutor: 도구 이름 -> 실제 실행. 워커 도구는 PlanningDepartment.run_partial로
1개만 재실행한다(검증·품질게이트·저장을 그대로 재사용). 결과는 context에 누적되어
다음 도구가 본다. focus 인자가 Phase A AgentDirective.instruction으로 들어간다.
"""
from core.directive import AgentDirective

TOOL_TO_AGENT = {
    "run_subject_analysis": "대상분석",
    "run_competition_analysis": "경쟁분석",
    "run_platform_recommendation": "플랫폼추천",
    "run_concept_planning": "컨셉기획",
}

_FINISH = "finish"


def _worker_tool(name, desc):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "이 분석에서 집중할 방향(선택). 대상자 특성에 맞춰 구체적으로.",
                    }
                },
                "required": [],
            },
        },
    }


WORKER_TOOLS = [
    _worker_tool("run_subject_analysis",
                 "대상자의 강점·약점·차별점을 분석한다. 보통 가장 먼저 호출한다."),
    _worker_tool("run_competition_analysis",
                 "유사 크리에이터·시장 공백을 웹 검색 기반으로 분석한다. 대상분석 이후가 좋다."),
    _worker_tool("run_platform_recommendation",
                 "1·2순위 플랫폼과 이유를 추천한다. 대상·경쟁 분석 이후가 좋다."),
    _worker_tool("run_concept_planning",
                 "컨셉 3개 + 4주 캘린더 + 촬영 가이드 + 해시태그를 기획한다. 보통 마지막."),
    {
        "type": "function",
        "function": {
            "name": _FINISH,
            "description": "필요한 분석을 모두 마쳤을 때 호출한다. summary에 종합 판단을 1~2줄.",
            "parameters": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": [],
            },
        },
    },
]


class ToolExecutor:
    def __init__(self, context: dict, planning_dept, event_emitter=None,
                 result_chars: int = 1800, measure_store=None):
        self.context = context
        self.dept = planning_dept
        self._emitter = event_emitter
        self.result_chars = result_chars
        self._measure = measure_store
        self.finished = False
        self.finish_summary = ""
        self.ran: list = []

    def _emit(self, t, d=None):
        if self._emitter:
            self._emitter.emit(t, d or {})

    def execute(self, name: str, args: dict) -> str:
        args = args or {}
        if name == _FINISH:
            self.finished = True
            self.finish_summary = str(args.get("summary", "")).strip()
            return "분석을 종료합니다."

        agent_name = TOOL_TO_AGENT.get(name)
        if not agent_name:
            return "알 수 없는 도구입니다: " + str(name)

        # Phase A seam: the model's focus becomes this agent's directive instruction.
        focus = str(args.get("focus", "")).strip()
        directives = self.context.setdefault("directives", {})
        directives[agent_name] = AgentDirective(
            strategy=self.context.get("ceo_summary", ""),
            instruction=focus,
            direction_md=self.context.get("방향", ""),
            feedback=self.context.get("피드백", ""),
            performance=self.context.get("성과_기록", ""),
        ).to_prompt_text()

        dept_result = self.dept.run_partial(self.context, [agent_name])
        for k, v in dept_result.agent_results.items():
            self.context[k] = v
        if agent_name not in self.ran:
            self.ran.append(agent_name)

        # Provenance: 모델이 스스로 이 워커를 호출하기로 결정 -> AI 결정으로 기록(감사용).
        # 측정은 절대 파이프라인을 깨면 안 된다 -> 예외 삼킴.
        if self._measure is not None:
            try:
                from core.measure import DecisionEntry, ACTOR_AI
                passed = dept_result.validation_results.get(agent_name, {}).get("passed", True)
                self._measure.log_decision(DecisionEntry(
                    actor=ACTOR_AI,
                    basis=("focus: " + focus) if focus else "자율 루프 도구 선택",
                    decision=(agent_name + " 실행") + ("" if passed else " (검증 미통과)"),
                ))
            except Exception as e:
                print("[ToolExecutor] 측정 로그 실패 (" + str(e) + ")")

        ck = self.dept.agents[agent_name].context_key
        content = dept_result.agent_results.get(ck, "") or "(빈 결과)"
        val = dept_result.validation_results.get(agent_name, {})
        note = "" if val.get("passed", True) else (chr(10) + "[주의: 품질 검증 미통과 -- 다음 단계에서 보완 고려]")
        return content[: self.result_chars] + note
