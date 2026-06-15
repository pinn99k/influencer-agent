"""AgentLoop 단위 테스트 (call_llm_tools mock)."""
from unittest.mock import patch, MagicMock

from core.agent_loop import AgentLoop


class FakeExec:
    def __init__(self):
        self.finished = False
        self.ran = []
        self.calls = []

    def execute(self, name, args):
        self.calls.append((name, args))
        if name == "finish":
            self.finished = True
            return "done"
        self.ran.append(name)
        return "result of " + name


def _msg(name, args="{}"):
    return {"role": "assistant", "content": None,
            "tool_calls": [{"id": "c", "type": "function",
                            "function": {"name": name, "arguments": args}}]}


def test_loop_runs_until_finish():
    seq = [_msg("run_subject_analysis"), _msg("run_competition_analysis"), _msg("finish")]
    ex = FakeExec()
    loop = AgentLoop(ex, [], "sys", max_iter=8)
    with patch("core.agent_loop.call_llm_tools", side_effect=seq):
        out = loop.run("go")
    assert out["finished"] is True
    assert out["ran"] == ["run_subject_analysis", "run_competition_analysis"]
    assert out["iterations"] == 3


def test_loop_max_iter_guard():
    ex = FakeExec()
    emitter = MagicMock()
    loop = AgentLoop(ex, [], "sys", max_iter=3, event_emitter=emitter)
    with patch("core.agent_loop.call_llm_tools", return_value=_msg("run_subject_analysis")):
        out = loop.run("go")
    assert out["iterations"] == 3
    assert out["finished"] is False
    types = [c.args[0] for c in emitter.emit.call_args_list if c.args]
    assert "loop_max_iter" in types


def test_loop_stops_on_no_toolcall():
    ex = FakeExec()
    final = {"role": "assistant", "content": "끝났습니다", "tool_calls": []}
    loop = AgentLoop(ex, [], "sys")
    with patch("core.agent_loop.call_llm_tools", return_value=final):
        out = loop.run("go")
    assert out["iterations"] == 1
    assert out["finished"] is False


def test_loop_feeds_tool_results_back():
    seq = [_msg("run_subject_analysis"), _msg("finish")]
    ex = FakeExec()
    loop = AgentLoop(ex, [], "sys")
    with patch("core.agent_loop.call_llm_tools", side_effect=seq):
        out = loop.run("go")
    tool_msgs = [m for m in out["messages"] if m.get("role") == "tool"]
    assert any("result of run_subject_analysis" in m["content"] for m in tool_msgs)
