"""AgentContext -- per-agent context access scope (V2 Spiral 5-A).

Each agent sees only the context keys permitted by AGENT_SCOPES. CEO has full
access. build_context returns read keys plus any permitted prior deliverables,
mapped from output filenames to their in-memory context_key (no disk reads).
"""

# display_name -> allowed scope.
#   read:      context dict keys this agent may receive ("*" = all)
#   knowledge: knowledge subdirectories injected into the agent's system prompt
#   outputs:   prior deliverable files the agent may read (active via _OUTPUT_TO_KEY)
#   tools:     external tools the agent may invoke (reserved for 5-B)
AGENT_SCOPES = {
    "CEO": {
        "read": ["*"],
        "knowledge": ["management/"],
        "outputs": ["*"],
    },
    "대상분석": {
        "read": ["대상자", "ceo_summary"],
        "knowledge": ["dept/planning/subject_analysis/"],
        "outputs": [],
    },
    "경쟁분석": {
        "read": ["대상자", "ceo_summary"],
        "knowledge": ["dept/planning/competition_analysis/"],
        "outputs": ["01_대상분석.md"],
        "tools": ["serper"],
    },
    "플랫폼추천": {
        "read": ["대상자", "ceo_summary"],
        "knowledge": ["dept/planning/platform_recommendation/"],
        "outputs": ["01_대상분석.md", "02_경쟁분석.md"],
    },
    "컨셉기획": {
        "read": ["대상자", "ceo_summary"],
        "knowledge": ["dept/planning/concept_planning/"],
        "outputs": ["01_대상분석.md", "02_경쟁분석.md", "03_플랫폼추천.md"],
    },
}


# Prior deliverable filename -> in-memory context_key.
# Lets scope['outputs'] grant access to a prior agent's result without disk I/O.
_OUTPUT_TO_KEY = {
    "01_대상분석.md": "대상_분석",
    "02_경쟁분석.md": "경쟁_분석",
    "03_플랫폼추천.md": "플랫폼_추천",
    "04_컨셉기획.md": "컨셉_기획",
}


def build_context(agent_name, full_context, file_manager=None):
    """Return a filtered copy of full_context per AGENT_SCOPES[agent_name].

    - Unknown agent_name -> copy of full_context (safe CEO-level fallback).
    - read contains "*" -> copy of full_context.
    - otherwise -> listed read keys + permitted prior outputs (mapped to
      their context_key) that exist in full_context.

    file_manager is accepted for forward compatibility but unused (in-memory).
    """
    scope = AGENT_SCOPES.get(agent_name)
    if scope is None:
        print(f"[AgentContext] 미등록 에이전트: {agent_name} — 전체 컨텍스트 반환")
        return dict(full_context)

    read_keys = scope.get("read", [])
    if "*" in read_keys:
        return dict(full_context)

    filtered = {k: full_context[k] for k in read_keys if k in full_context}

    # Grant permitted prior deliverables via their in-memory context_key.
    for out_file in scope.get("outputs", []):
        key = _OUTPUT_TO_KEY.get(out_file)
        if key and key in full_context and key not in filtered:
            filtered[key] = full_context[key]

    # Phase A: deliver this agent's per-agent directive (CEO strategy + its
    # specific instruction + user direction/feedback) through the ceo_summary key
    # the worker already reads. Falls back to the general ceo_summary otherwise.
    directives = full_context.get("directives")
    if directives and agent_name in directives:
        filtered["ceo_summary"] = directives[agent_name]

    return filtered
