"""Regression tests for the reanalysis feedback-reflection fix.

Before the fix, user feedback only steered _decide_rerun (which agents re-run);
the re-run agents never saw the feedback because:
  1. _build_ceo_summary built ceo_summary from 대상자 only, and
  2. build_prompt serialized only get_context_keys() (no ceo_summary).

These tests lock both gates: feedback lands in ceo_summary verbatim, and
ceo_summary reaches every agent's prompt.
"""
from unittest.mock import MagicMock, patch

from agents.subject_analyst import SubjectAnalystAgent
from agents.competition_analyst import CompetitionAnalystAgent
from agents.platform_recommender import PlatformRecommenderAgent
from agents.concept_planner import ConceptPlannerAgent
from tests.conftest import SAMPLE_SUBJECT

# ASCII marker stands in for a specific user correction (e.g. "컨셉 B로 바꿔줘").
MARKER = "SWITCH_CONCEPT_TO_B_2026"


def _ceo():
    from agents.ceo import CEO
    return CEO(MagicMock(), dry_run=False)


# ---- Gate 1: feedback reaches ceo_summary verbatim ------------------------

def test_build_ceo_summary_appends_feedback_verbatim():
    ctx = {"대상자": {"이름": "Test"}, "피드백": MARKER}
    with patch("agents.ceo.call_llm", return_value="전략 요약"):
        _ceo()._build_ceo_summary(ctx)
    assert MARKER in ctx["ceo_summary"]


def test_build_ceo_summary_no_feedback_unchanged():
    ctx = {"대상자": {"이름": "Test"}}
    with patch("agents.ceo.call_llm", return_value="전략 요약"):
        _ceo()._build_ceo_summary(ctx)
    assert ctx["ceo_summary"] == "전략 요약"
    assert MARKER not in ctx["ceo_summary"]


# ---- Gate 2: ceo_summary reaches each agent's prompt ----------------------

def _ctx_with_directive():
    return {
        "대상자": SAMPLE_SUBJECT,
        "대상_분석": "x", "경쟁_분석": "y", "플랫폼_추천": "z",
        "ceo_summary": "전략 요약\n\n[사용자 피드백 - 반드시 반영]\n" + MARKER,
    }


def test_subject_prompt_includes_directive():
    assert MARKER in SubjectAnalystAgent().build_prompt(_ctx_with_directive())


def test_platform_prompt_includes_directive():
    assert MARKER in PlatformRecommenderAgent().build_prompt(_ctx_with_directive())


def test_concept_prompt_includes_directive():
    assert MARKER in ConceptPlannerAgent().build_prompt(_ctx_with_directive())


def test_competition_prompt_includes_directive():
    ctx = _ctx_with_directive()
    ctx["serper_results"] = []
    ctx["search_queries"] = []
    assert MARKER in CompetitionAnalystAgent().build_prompt(ctx)


def test_no_directive_when_summary_absent():
    # First analysis without ceo_summary -> no injected directive key.
    ctx = {"대상자": SAMPLE_SUBJECT}
    prompt = SubjectAnalystAgent().build_prompt(ctx)
    assert "ceo_전략_지시" not in prompt
