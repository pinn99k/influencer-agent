"""DirectionProfile — the user-chosen strategic direction.

Even when a final goal exists, the *direction* is the user's to set. This model
captures it as structured data (content focus / target goal / strategy focus /
notes) and renders it for two purposes:
  - to_markdown / from_markdown : persistence in outputs/{name}/방향.md
  - to_prompt_text              : compact directive injected into ceo_summary so
                                  agents actually shape their output to it.

Kept free of disk/LLM concerns (SRP). FileManager persists; CEO injects.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Section headers — single source of truth for to/from_markdown symmetry.
_H_CONTENT = "## 콘텐츠 방향"
_H_GOAL = "## 핵심 목표"
_H_STRATEGY = "## 중점 전략"
_H_NOTES = "## 메모"


@dataclass
class DirectionProfile:
    content_focus: str = ""           # 콘텐츠 방향 (예: 연습영상 위주)
    target_goal: str = ""             # 핵심 목표 (예: 팔로워 100만)
    strategy_focus: list[str] = field(default_factory=list)  # 중점 전략 영역
    notes: str = ""                   # 자유 메모

    def is_empty(self) -> bool:
        return not (
            self.content_focus.strip()
            or self.target_goal.strip()
            or [s for s in self.strategy_focus if s.strip()]
            or self.notes.strip()
        )

    def to_markdown(self, name: str = "") -> str:
        lines = ["# 방향"]
        if name:
            lines.append(f"**대상자:** {name}")
        lines += ["", _H_CONTENT, self.content_focus.strip()]
        lines += ["", _H_GOAL, self.target_goal.strip()]
        lines += ["", _H_STRATEGY]
        lines += [f"- {s.strip()}" for s in self.strategy_focus if s.strip()]
        lines += ["", _H_NOTES, self.notes.strip(), ""]
        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, text: str) -> "DirectionProfile":
        sections = cls._split_sections(text or "")
        strategy_raw = sections.get(_H_STRATEGY, "")
        strategy = [
            ln.lstrip("-* ").strip()
            for ln in strategy_raw.splitlines()
            if ln.strip().startswith(("-", "*"))
        ]
        return cls(
            content_focus=sections.get(_H_CONTENT, "").strip(),
            target_goal=sections.get(_H_GOAL, "").strip(),
            strategy_focus=[s for s in strategy if s],
            notes=sections.get(_H_NOTES, "").strip(),
        )

    def to_prompt_text(self) -> str:
        """Compact directive for ceo_summary injection. Empty fields omitted."""
        if self.is_empty():
            return ""
        parts = ["[사용자가 정한 방향 — 전략에 반드시 반영]"]
        if self.content_focus.strip():
            parts.append(f"- 콘텐츠 방향: {self.content_focus.strip()}")
        if self.target_goal.strip():
            parts.append(f"- 핵심 목표: {self.target_goal.strip()}")
        focus = [s.strip() for s in self.strategy_focus if s.strip()]
        if focus:
            parts.append(f"- 중점 전략: {', '.join(focus)}")
        if self.notes.strip():
            parts.append(f"- 메모: {self.notes.strip()}")
        return "\n".join(parts)

    @staticmethod
    def _split_sections(text: str) -> dict:
        """Map each '## ' header to the text block beneath it (until next '## ')."""
        sections: dict = {}
        current = None
        buf: list[str] = []
        for line in text.splitlines():
            if line.startswith("## "):
                if current is not None:
                    sections[current] = "\n".join(buf).strip()
                current = line.strip()
                buf = []
            elif current is not None:
                buf.append(line)
        if current is not None:
            sections[current] = "\n".join(buf).strip()
        return sections


# Placeholder values that mean "the user has not actually set this" — treated as empty.
_DIRECTION_PLACEHOLDERS = {"", "미정", "정보 없음"}


def direction_has_content(markdown: str) -> bool:
    """True if a saved 방향.md holds any real user signal.

    Placeholders (미정 / 정보 없음) and bare headers count as empty, so an
    all-미정 direction does NOT count as a reanalysis input.
    """
    if not markdown or not markdown.strip():
        return False
    # Line scan (handles both the ## section format AND chat-appended "- text"
    # bullets). A line counts as signal unless it is a header, the **대상자:** meta
    # line, a bare bullet, or a placeholder (미정 / 정보 없음).
    for line in markdown.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("**"):
            continue
        s = s.lstrip("-*").strip()
        if not s or s in _DIRECTION_PLACEHOLDERS:
            continue
        return True
    return False
