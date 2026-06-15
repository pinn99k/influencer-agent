"""Integration tests: PlanningDepartment._run_agent + AgentOutput (Spiral 5-A)."""
import json
from unittest.mock import MagicMock, patch

from departments.planning import PlanningDepartment, DepartmentResult
from agents.agent_output import _DELIM_START, _DELIM_END


def _make_dept():
    fm = MagicMock()
    with patch("departments.planning.AGENT_CLASSES", []):
        dept = PlanningDepartment(fm)
    dept._compress_result = MagicMock(return_value="요약")
    dept._judge_quality = MagicMock(return_value={"score": 90})
    return dept, fm


def _agent(context_key="대상_분석", output_prefix="01"):
    a = MagicMock()
    a.context_key = context_key
    a.output_prefix = output_prefix
    return a


def _ctx():
    return {"대상자": {"이름": "테스트"}}


def _with_block(payload):
    return f"## 분석\n본문\n\n{_DELIM_START}\n{json.dumps(payload, ensure_ascii=False)}\n{_DELIM_END}"


def _run(dept, agent, ctx, result):
    with patch("departments.planning.OutputValidator") as mv:
        mv.validate.return_value = MagicMock(passed=True, failed_rules=[])
        dept._run_agent("대상분석", agent, ctx, result)
        return mv


class TestRunAgentAgentOutput:
    def test_parses_questions_comments_confidence(self):
        dept, fm = _make_dept()
        agent = _agent()
        agent.run.return_value = _with_block({
            "questions": ["타겟을 좁힐까요?"],
            "comments": ["릴스를 권합니다"],
            "confidence": 0.7,
        })
        result = DepartmentResult()
        _run(dept, agent, _ctx(), result)
        assert result.agent_questions["대상분석"] == ["타겟을 좁힐까요?"]
        assert result.agent_comments["대상분석"] == ["릴스를 권합니다"]
        assert result.agent_confidence["대상분석"] == 0.7

    def test_content_only_propagated(self):
        dept, fm = _make_dept()
        agent = _agent()
        agent.run.return_value = _with_block({"confidence": 0.9})
        result = DepartmentResult()
        _run(dept, agent, _ctx(), result)
        assert result.agent_results["대상_분석"] == "## 분석\n본문"

    def test_validator_receives_content_not_raw(self):
        dept, fm = _make_dept()
        agent = _agent()
        agent.run.return_value = _with_block({"confidence": 0.9})
        result = DepartmentResult()
        mv = _run(dept, agent, _ctx(), result)
        passed_content = mv.validate.call_args[0][1]
        assert _DELIM_START not in passed_content
        assert passed_content == "## 분석\n본문"

    def test_save_output_receives_content(self):
        dept, fm = _make_dept()
        agent = _agent()
        agent.run.return_value = _with_block({"confidence": 0.9})
        result = DepartmentResult()
        _run(dept, agent, _ctx(), result)
        saved = fm.save_output.call_args[0][2]
        assert _DELIM_START not in saved

    def test_save_raw_keeps_full_block(self):
        dept, fm = _make_dept()
        agent = _agent()
        agent.run.return_value = _with_block({"confidence": 0.9})
        result = DepartmentResult()
        _run(dept, agent, _ctx(), result)
        saved_raw = fm.save_raw.call_args[0][1]
        assert _DELIM_START in saved_raw

    def test_plain_string_backward_compat(self):
        dept, fm = _make_dept()
        agent = _agent()
        agent.run.return_value = "## 그냥 마크다운 결과"
        result = DepartmentResult()
        _run(dept, agent, _ctx(), result)
        assert result.agent_results["대상_분석"] == "## 그냥 마크다운 결과"
        assert "대상분석" not in result.agent_questions
        assert result.agent_confidence["대상분석"] == 1.0
