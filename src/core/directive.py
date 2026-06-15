"""AgentDirective -- structured, per-agent strategic directive (Phase A).

Replaces the single fragile ceo_summary string. Carries the CEO's overall
strategy PLUS this agent's specific instruction (previously orphaned in plan.md)
PLUS the user's chosen direction/feedback/performance.

In Phase 2 (tool-calling loop) this IS the payload the orchestrator passes when
it invokes a worker-as-tool. The pipeline is just one driver of the same seam.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.direction import DirectionProfile, direction_has_content


@dataclass
class AgentDirective:
    strategy: str = ""        # CEO overall strategic direction
    instruction: str = ""     # THIS agent's specific focus (from the CEO plan)
    direction_md: str = ""    # raw 방향.md (user-set direction)
    feedback: str = ""        # user feedback (reanalysis correction)
    performance: str = ""     # performance data

    def _direction_text(self) -> str:
        if not self.direction_md or not direction_has_content(self.direction_md):
            return ""
        structured = DirectionProfile.from_markdown(self.direction_md).to_prompt_text()
        if structured:
            return structured
        # Chat-appended directions live as bare "- text" bullets (no ## section),
        # which from_markdown misses -> fall back to raw verbatim when meaningful.
        if direction_has_content(self.direction_md):
            return "[사용자가 정한 방향 — 전략에 반드시 반영]\n" + self.direction_md.strip()
        return ""

    def to_prompt_text(self) -> str:
        parts = []
        if self.strategy.strip():
            parts.append("[CEO 전략 방향]\n" + self.strategy.strip())
        if self.instruction.strip():
            parts.append("[이 에이전트를 향한 핵심 지시]\n" + self.instruction.strip())
        dir_text = self._direction_text()
        if dir_text:
            parts.append(dir_text)
        if self.feedback.strip():
            parts.append("[사용자 피드백 — 반드시 반영]\n" + self.feedback.strip())
        if self.performance.strip():
            parts.append("[성과 데이터]\n" + self.performance.strip()[:500])
        return "\n\n".join(parts)
