import datetime

from core.file_manager import FileManager


class ReportBuilder:
    """ReportBuilder: briefing/rework/final report/handover/plan text generation.
    SRP: text composition only - file saving delegated to FileManager."""

    def __init__(self, file_manager: FileManager):
        self._fm = file_manager

    # -- Chairman report --

    def build_briefing(self, condition_no: int, context: dict, state: dict) -> str:
        subject_name = context.get("대상자", {}).get("이름", "미상")
        return (
            f"## 회장 보고\n"
            f"보고 조건: {condition_no}\n"
            f"대상자: {subject_name}\n"
            f"현재 상태: {state}\n"
            f"\n결정 요청: 계속 진행(A) 또는 중단(B)"
        )

    # -- Rework instructions --

    def build_rework_instruction(self, agent_name: str, val_result) -> str:
        rules_text = "\n".join(f"- {r}" for r in val_result.failed_rules)
        return (
            f"## 재작업 지시 — {agent_name}\n\n"
            f"### 실패 규칙\n{rules_text}\n\n"
            f"### 수정 방향\n"
            f"1. 위 실패 규칙을 모두 충족하도록 결과를 다시 작성하세요.\n"
            f"2. FORMAT 섹션 헤더를 정확히 포함하세요.\n"
            f"3. 대상자 이름을 반드시 포함하세요."
        )

    def build_quality_rework(self, agent_name: str) -> str:
        return (
            f"## 재작업 지시 (품질) — {agent_name}\n\n"
            f"CEO 판단: 다음 에이전트가 활용하기에 품질이 부족합니다.\n\n"
            f"### 수정 방향\n"
            f"1. 대상자 정보가 구체적으로 반영되어 있는지 확인하세요.\n"
            f"2. Generic한 내용(누구에게나 해당되는 조언)을 제거하세요.\n"
            f"3. 각 항목에 구체적인 근거를 추가하세요."
        )

    # -- Final report --

    def build_final_report(self, context: dict, key_labels: list[tuple[str, str]]) -> str:
        """Fallback only; normal path is CEO._synthesize_final_report."""
        subject = context.get("대상자", {})
        lines = [
            f"# 최종 리포트 — {subject.get('이름', '')}",
            f"생성일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        for key, label in key_labels:
            if context.get(key):
                lines.append(f"---\n\n{context[key]}\n")
        return "\n".join(lines)

    # -- Handover --

    def build_handover(self, context: dict, agent_order: list, completed: list) -> str:
        subject = context.get("대상자", {})
        return (
            f"# 인수인계 문서\n"
            f"생성일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"대상자: {subject.get('이름', '')}\n\n"
            f"## 완료된 작업\n"
            + "\n".join(f"- [x] {a}" for a in completed)
            + "\n\n## 다음 세션 컨텍스트 로드 순서\n"
            f"1. CLAUDE.md\n2. docs/workflow/status.md\n"
            f"3. outputs/{subject.get('이름', '')}/인수인계/ (이 파일)\n"
        )

    # -- Execution plan --

    def build_plan(self, completed: list, remaining: list) -> str:
        # Progress tracker (saved to progress.md). The strategic plan lives in
        # plan.md and is produced by CEO._interpret_goal — keep them separate.
        return (
            f"# CEO 진행 상황\n"
            f"updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"## 완료\n" + "\n".join(f"- [x] {a}" for a in completed) + "\n\n"
            f"## 남은 에이전트\n" + "\n".join(f"- [ ] {a}" for a in remaining)
        )
