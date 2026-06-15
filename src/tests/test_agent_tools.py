"""ToolExecutor + WORKER_TOOLS 단위 테스트 (dept mock)."""
from unittest.mock import MagicMock

from core.tools import ToolExecutor, WORKER_TOOLS


def _dept(agent_name, ck, content, passed=True):
    dept = MagicMock()
    res = MagicMock()
    res.agent_results = {ck: content}
    res.validation_results = {agent_name: {"passed": passed}}
    dept.run_partial.return_value = res
    agent = MagicMock()
    agent.context_key = ck
    dept.agents = {agent_name: agent}
    return dept


def test_worker_tool_runs_and_merges():
    dept = _dept("대상분석", "대상_분석", "분석 결과 텍스트")
    ctx = {"대상자": {"이름": "T"}}
    ex = ToolExecutor(ctx, dept)
    out = ex.execute("run_subject_analysis", {"focus": "헤어컬러 강조"})
    assert "분석 결과 텍스트" in out
    assert ex.ran == ["대상분석"]
    assert ctx["대상_분석"] == "분석 결과 텍스트"
    assert "헤어컬러 강조" in ctx["directives"]["대상분석"]


def test_unverified_adds_note():
    dept = _dept("경쟁분석", "경쟁_분석", "경쟁 텍스트", passed=False)
    ex = ToolExecutor({"대상자": {"이름": "T"}}, dept)
    out = ex.execute("run_competition_analysis", {})
    assert "검증 미통과" in out


def test_finish():
    ex = ToolExecutor({}, MagicMock())
    out = ex.execute("finish", {"summary": "끝"})
    assert ex.finished is True
    assert ex.finish_summary == "끝"


def test_unknown_tool():
    ex = ToolExecutor({}, MagicMock())
    out = ex.execute("nope", {})
    assert "알 수 없는" in out


def test_tool_schema_complete():
    names = {tt["function"]["name"] for tt in WORKER_TOOLS}
    assert names == {"run_subject_analysis", "run_competition_analysis",
                     "run_platform_recommendation", "run_concept_planning", "finish"}
