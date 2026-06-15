"""AgentOutput -- structured agent return type (V2 Spiral 5-A).

Agents still return ``str`` from ``run()``; PlanningDepartment wraps the raw
string with ``AgentOutput.from_raw()`` at a single point. Parsing is lenient:
any input yields a valid AgentOutput, so legacy plain-string outputs keep
working unchanged.

Structured block format (optional, appended after the markdown content):

    (markdown content)

    ---AGENT_OUTPUT---
    {
      "questions": ["..."],
      "comments": ["..."],
      "confidence": 0.75,
      "metadata": {"search_queries": ["..."]}
    }
    ---END_OUTPUT---
"""
import json
from dataclasses import dataclass, field

_DELIM_START = "---AGENT_OUTPUT---"
_DELIM_END = "---END_OUTPUT---"


@dataclass
class AgentOutput:
    content: str
    questions: list = field(default_factory=list)
    comments: list = field(default_factory=list)
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_raw(cls, text) -> "AgentOutput":
        """Parse raw LLM text into AgentOutput. Never raises.

        Rules:
          1. No ---AGENT_OUTPUT--- block -> entire text is content (legacy path).
          2. Block present + valid JSON -> split content / structured fields.
          3. Block present + broken JSON -> whole text (delimiters stripped) as content.
        """
        if not text:
            return cls(content="")

        start = text.find(_DELIM_START)
        if start == -1:
            # No structured block -- backward compatible
            return cls(content=text.strip())

        content = text[:start].rstrip()
        rest = text[start + len(_DELIM_START):]
        end = rest.find(_DELIM_END)
        json_str = rest[:end] if end != -1 else rest

        try:
            data = json.loads(json_str.strip())
        except (ValueError, TypeError):
            cleaned = text.replace(_DELIM_START, "").replace(_DELIM_END, "").strip()
            return cls(content=cleaned)

        if not isinstance(data, dict):
            cleaned = text.replace(_DELIM_START, "").replace(_DELIM_END, "").strip()
            return cls(content=cleaned)

        meta = data.get("metadata")
        return cls(
            content=content,
            questions=cls._clean_list(data.get("questions")),
            comments=cls._clean_list(data.get("comments")),
            confidence=cls._clip_confidence(data.get("confidence")),
            metadata=meta if isinstance(meta, dict) else {},
        )

    @staticmethod
    def _clean_list(value) -> list:
        """Coerce to a list of non-empty strings; anything else -> []."""
        if not isinstance(value, list):
            return []
        out = []
        for item in value:
            if isinstance(item, bool):
                continue
            if isinstance(item, (str, int, float)):
                s = str(item).strip()
                if s:
                    out.append(s)
        return out

    @staticmethod
    def _clip_confidence(value) -> float:
        """Clip numeric confidence to [0.0, 1.0]; non-numeric -> 1.0 default."""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return 1.0
        return min(1.0, max(0.0, float(value)))
