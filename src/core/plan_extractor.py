import re


def extract_weeks(concept_output: str) -> list[dict]:
    """Extract Week 1-4 content items from concept planning output."""
    weeks = []
    for n in (1, 2, 3, 4):
        m = re.search(rf"####\s*Week\s*{n}\b", concept_output)
        items = []
        if m:
            rest = concept_output[m.end():]
            nxt = re.search(r"\n####\s|\n###\s", rest)
            body = rest[:nxt.start()] if nxt else rest
            for line in body.splitlines():
                s = line.strip()
                if re.match(r"^(\d+\.|[-*])\s+", s):
                    items.append(re.sub(r"^(\d+\.|[-*])\s+", "", s))
        weeks.append({"num": n, "items": items})
    return weeks


def _extract_list_section(report: str, header: str) -> list[str]:
    """Extract markdown list items from a level-2 section."""
    m = re.search(rf"##\s*{re.escape(header)}\b", report)
    if not m:
        return []
    rest = report[m.end():]
    nxt = re.search(r"\n##\s", rest)
    body = rest[:nxt.start()] if nxt else rest
    out = []
    for line in body.splitlines():
        s = line.strip()
        if re.match(r"^(\d+\.|[-*])\s+", s):
            out.append(re.sub(r"^(\d+\.|[-*])\s+", "", s))
    return out


def extract_plan(concept_output: str = "", final_report: str = "") -> dict:
    return {
        "weeks": extract_weeks(concept_output or ""),
        "next_actions": _extract_list_section(final_report or "", "지금 당장 할 3가지"),
        "kpi": (
            _extract_list_section(final_report or "", "성공 지표 (30일)")
            or _extract_list_section(final_report or "", "성공 지표")
        ),
    }
