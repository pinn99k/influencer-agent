"""P2 tests — Track 0 runtime visibility: CEO judgment fallbacks must EMIT.

The 6 CEO LLM judgments swallow exceptions and fall back silently (operational
safety — kept). But silence hides degradation: "CEO.run() passed" proves nothing
if every judgment fell back. These tests pin that each fallback path emits a
'judgment_fallback' event so the web UI / logs can show it at runtime.
"""
from unittest.mock import MagicMock, patch

import pytest


def _ceo_with_emitter():
    from agents.ceo import CEO
    fm = MagicMock()
    fm.name = "FallbackTest"
    emitter = MagicMock()
    return CEO(fm, dry_run=False, event_emitter=emitter), emitter


def _fallback_events(emitter):
    return [c.args for c in emitter.emit.call_args_list
            if c.args and c.args[0] == "judgment_fallback"]


def _boom(*a, **k):
    raise RuntimeError("llm down")


def test_build_ceo_summary_fallback_emits():
    ceo, emitter = _ceo_with_emitter()
    with patch("agents.ceo.call_llm", side_effect=_boom):
        ceo._build_ceo_summary({"대상자": {"이름": "T"}})
    events = _fallback_events(emitter)
    assert len(events) == 1
    assert events[0][1]["method"] == "_build_ceo_summary"
    assert "llm down" in events[0][1]["error"]


def test_decide_rerun_fallback_emits():
    ceo, emitter = _ceo_with_emitter()
    ctx = {"대상자": {"이름": "T"}, "피드백": "x"}
    with patch("agents.ceo.call_llm", side_effect=_boom):
        ceo._decide_rerun(ctx)
    events = _fallback_events(emitter)
    assert len(events) == 1
    assert events[0][1]["method"] == "_decide_rerun"


def test_interpret_goal_fallback_emits():
    ceo, emitter = _ceo_with_emitter()
    with patch("agents.ceo.call_llm", side_effect=_boom):
        ceo._interpret_goal({"대상자": {"이름": "T", "목표": "g"}})
    events = _fallback_events(emitter)
    assert len(events) == 1
    assert events[0][1]["method"] == "_interpret_goal"


def test_no_fallback_no_emit():
    ceo, emitter = _ceo_with_emitter()
    with patch("agents.ceo.call_llm", return_value="정상 요약"):
        ceo._build_ceo_summary({"대상자": {"이름": "T"}})
    assert _fallback_events(emitter) == []
