"""T1 자율 루프 관찰성 -- 도구호출 provenance 로깅 + 루프 종료 사유."""
from unittest.mock import patch

from core.tools import ToolExecutor
from core.agent_loop import AgentLoop
from core.measure import ACTOR_AI
from departments.planning import DepartmentResult


class _RecMeasure:
    def __init__(self):
        self.logged = []

    def log_decision(self, entry):
        self.logged.append(entry)


class _StubAgent:
    context_key = "대상_분석"


class _StubDept:
    def __init__(self):
        self.agents = {"대상분석": _StubAgent()}

    def run_partial(self, ctx, names):
        r = DepartmentResult()
        r.agent_results = {"대상_분석": "분석 내용"}
        r.validation_results = {"대상분석": {"passed": True}}
        return r


# ── ToolExecutor provenance ──

def test_tool_executor_logs_ai_decision():
    m = _RecMeasure()
    ex = ToolExecutor({"대상자": {"이름": "T"}}, _StubDept(), measure_store=m)
    ex.execute("run_subject_analysis", {"focus": "강점 위주"})
    assert len(m.logged) == 1
    assert m.logged[0].actor == ACTOR_AI
    assert "대상분석" in m.logged[0].decision
    assert "강점 위주" in m.logged[0].basis


def test_tool_executor_finish_does_not_log():
    m = _RecMeasure()
    ex = ToolExecutor({}, _StubDept(), measure_store=m)
    ex.execute("finish", {"summary": "끝"})
    assert m.logged == []


def test_tool_executor_without_measure_is_safe():
    ex = ToolExecutor({"대상자": {"이름": "T"}}, _StubDept())  # measure_store=None
    out = ex.execute("run_subject_analysis", {"focus": "x"})
    assert "분석 내용" in out


# ── AgentLoop 종료 사유 ──

class _FE:
    def __init__(self):
        self.finished = False
        self.ran = []

    def execute(self, name, args):
        if name == "finish":
            self.finished = True
            return "done"
        self.ran.append(name)
        return "r"


def _tcmsg(name):
    return {"role": "assistant", "content": None,
            "tool_calls": [{"id": "c", "function": {"name": name, "arguments": "{}"}}]}


def test_stop_reason_finish():
    loop = AgentLoop(_FE(), [], "sys")
    with patch("core.agent_loop.call_llm_tools",
               side_effect=[_tcmsg("run_subject_analysis"), _tcmsg("finish")]):
        out = loop.run("go")
    assert out["stop_reason"] == "finish"


def test_stop_reason_no_tool():
    loop = AgentLoop(_FE(), [], "sys")
    with patch("core.agent_loop.call_llm_tools",
               return_value={"role": "assistant", "content": "끝", "tool_calls": []}):
        out = loop.run("go")
    assert out["stop_reason"] == "no_tool"


def test_stop_reason_max_iter():
    loop = AgentLoop(_FE(), [], "sys", max_iter=2)
    with patch("core.agent_loop.call_llm_tools", return_value=_tcmsg("run_subject_analysis")):
        out = loop.run("go")
    assert out["stop_reason"] == "max_iter"
    assert out["iterations"] == 2
