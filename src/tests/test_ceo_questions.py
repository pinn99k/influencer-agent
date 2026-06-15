"""Unit tests for CEO._handle_agent_questions (Spiral 5-B B4)."""
import json
from unittest.mock import MagicMock, patch

from agents.ceo import CEO


def _ceo():
    fm = MagicMock()
    c = CEO(fm, dry_run=False)
    c._emit = MagicMock()
    c._prompts.load_prompt = MagicMock(return_value="SYS")
    return c


def _ctx(qmap):
    return {"대상자": {"이름": "테스트"}, "에이전트_질문": qmap}


class TestHandleAgentQuestions:
    def test_empty_questions(self):
        c = _ceo()
        ctx = _ctx({})
        c._handle_agent_questions(ctx)
        r = ctx["질문_응답"]
        assert r == {"answers": {}, "escalated": [], "data_requests": []}

    def test_routing_three_types(self):
        c = _ceo()
        ctx = _ctx({"대상분석": ["타겟을 좁힐까요?", "범위는?"], "경쟁분석": ["경력 연수가 없습니다"]})
        classifications = {"classifications": [
            {"question": "타겟을 좁힐까요?", "type": "STRATEGIC", "answer": None},
            {"question": "범위는?", "type": "TACTICAL", "answer": "미용사 중심으로 본다"},
            {"question": "경력 연수가 없습니다", "type": "DATA", "answer": None},
        ]}
        with patch("agents.ceo.call_llm", return_value=json.dumps(classifications, ensure_ascii=False)):
            c._handle_agent_questions(ctx)
        r = ctx["질문_응답"]
        assert "타겟을 좁힐까요?" in r["escalated"]
        assert r["answers"]["범위는?"] == "미용사 중심으로 본다"
        assert "경력 연수가 없습니다" in r["data_requests"]

    def test_data_with_answer_goes_to_answers(self):
        c = _ceo()
        ctx = _ctx({"대상분석": ["직업이 뭔가요?"]})
        classifications = {"classifications": [
            {"question": "직업이 뭔가요?", "type": "DATA", "answer": "미용사"},
        ]}
        with patch("agents.ceo.call_llm", return_value=json.dumps(classifications, ensure_ascii=False)):
            c._handle_agent_questions(ctx)
        assert ctx["질문_응답"]["answers"]["직업이 뭔가요?"] == "미용사"
        assert ctx["질문_응답"]["data_requests"] == []

    def test_llm_failure_escalates_all(self):
        c = _ceo()
        ctx = _ctx({"대상분석": ["q1", "q2"]})
        with patch("agents.ceo.call_llm", side_effect=RuntimeError("boom")):
            c._handle_agent_questions(ctx)
        assert set(ctx["질문_응답"]["escalated"]) == {"q1", "q2"}

    def test_dry_run_skips(self):
        c = _ceo()
        c.dry_run = True
        ctx = _ctx({"대상분석": ["q1"]})
        c._handle_agent_questions(ctx)
        assert ctx["질문_응답"]["escalated"] == []
