"""U4 tests — ChatEngine (context-aware multiturn CEO chat).

LLM is patched (core.chat_engine.call_llm_messages) so these are pure unit tests.
ChatEngine grounds replies in the influencer's strategy context and captures a
direction when the user states one.
"""
from unittest.mock import MagicMock, patch

import pytest

from core.chat_engine import ChatEngine, ChatResponse


def _fm(**over):
    fm = MagicMock()
    fm.load_final_report.return_value = over.get("report", "전략 리포트 본문")
    fm.load_existing_outputs.return_value = over.get("outputs", {})
    fm.load_direction.return_value = over.get("direction", None)
    fm.load_performance_record.return_value = over.get("perf", None)
    fm.load_feedback.return_value = over.get("feedback", None)
    return fm


def _engine(**over):
    return ChatEngine(_fm(**over))


def test_start_returns_greeting():
    with patch("core.chat_engine.call_llm_messages", return_value='{"message": "안녕하세요, 대표예요."}'):
        assert _engine().start() == "안녕하세요, 대표예요."


def test_reply_returns_message():
    with patch("core.chat_engine.call_llm_messages", return_value='{"message": "해시태그 전략은 이렇습니다."}'):
        r = _engine().reply("해시태그 전략 알려줘")
    assert isinstance(r, ChatResponse)
    assert r.message == "해시태그 전략은 이렇습니다."


def test_reply_captures_direction():
    out = '{"message": "연습영상 위주로 잡을게요.", "direction_update": "콘텐츠: 연습영상 위주"}'
    with patch("core.chat_engine.call_llm_messages", return_value=out):
        r = _engine().reply("콘텐츠는 연습영상 위주로 할거야")
    assert r.captured_direction == "콘텐츠: 연습영상 위주"


def test_reply_no_direction_default_empty():
    with patch("core.chat_engine.call_llm_messages", return_value='{"message": "네"}'):
        r = _engine().reply("그냥 질문이야")
    assert r.captured_direction == ""


def test_history_accumulates():
    eng = _engine()
    with patch("core.chat_engine.call_llm_messages", return_value='{"message": "답변"}'):
        eng.reply("질문1")
        eng.reply("질문2")
    # 2 user + 2 assistant
    assert len(eng.history) == 4


def test_context_block_includes_report_and_direction():
    eng = _engine(report="최종 전략 X", direction="- 콘텐츠 방향: 연습영상")
    block = eng._build_context_block()
    assert "최종 전략 X" in block
    assert "연습영상" in block


def test_context_block_falls_back_to_outputs_when_no_report():
    eng = _engine(report=None, outputs={"대상_분석": "분석 본문 ABC"})
    block = eng._build_context_block()
    assert "분석 본문 ABC" in block


def test_reply_empty_message_guarded():
    eng = _engine()
    with patch("core.chat_engine.call_llm_messages") as m:
        r = eng.reply("   ")
        m.assert_not_called()
    assert r.message  # some guard message


def test_llm_failure_graceful():
    def boom(*a, **k):
        raise RuntimeError("down")
    with patch("core.chat_engine.call_llm_messages", side_effect=boom):
        r = _engine().reply("질문")
    assert isinstance(r, ChatResponse)
    assert r.message  # fallback, no crash
