"""Unit tests for InterviewEngine (V2 Spiral 5-C, refactored).

New model: dialogue (reply) and submission (confirm) are independent.
- reply works until confirmed; emitting a summary does NOT end the dialogue.
- can_submit() is computed from extracted data (name + >=4 required fields).
LLM mocked.
"""
import json
from unittest.mock import patch

import pytest

from core.interview_engine import InterviewEngine, InterviewResponse


# A set of 4 required fields incl. name -> satisfies can_submit().
_SUBMITTABLE = {"이름": "김민수", "직업": "미용사", "목표": "구독자 1000명", "특기": "염색"}


def _resp(rtype="question", message="다음 질문입니다", extracted=None, sufficient=False):
    return json.dumps(
        {"type": rtype, "message": message,
         "extracted_so_far": extracted or {}, "sufficient": sufficient},
        ensure_ascii=False,
    )


def _patch(seq):
    """call_llm_messages를 시퀀스/단일값으로 패치."""
    if isinstance(seq, list):
        return patch("core.interview_engine.call_llm_messages", side_effect=seq)
    return patch("core.interview_engine.call_llm_messages", return_value=seq)


class TestDialogue:
    def test_start_returns_greeting(self):
        e = InterviewEngine()
        with _patch(_resp(message="안녕하세요! 성함이 어떻게 되세요?")):
            g = e.start()
        assert g and "안녕" in g
        assert e.conversation[-1]["role"] == "assistant"

    def test_reply_returns_interview_response(self):
        e = InterviewEngine()
        with _patch(_resp(extracted={"이름": "김민수"})):
            r = e.reply("김민수입니다")
        assert isinstance(r, InterviewResponse)
        assert r.turn_count == 1

    def test_extracted_fields_accumulate(self):
        e = InterviewEngine()
        with _patch([_resp(extracted={"이름": "김민수"}),
                     _resp(extracted={"직업": "미용사"})]):
            e.reply("김민수입니다")
            e.reply("미용사예요")
        assert e.extracted["이름"] == "김민수"
        assert e.extracted["직업"] == "미용사"

    def test_empty_input_handling(self):
        e = InterviewEngine()
        r = e.reply("   ")                   # LLM 호출 없음
        assert r.type == "question"
        assert e.turn_count == 0

    def test_json_parse_failure_fallback(self):
        e = InterviewEngine()
        with _patch("이건 JSON이 아닙니다 그냥 텍스트"):
            r = e.reply("안녕하세요")
        assert r.type == "question"
        assert "JSON이 아닙니다" in r.message


class TestSubmitGate:
    """can_submit() is data-driven, independent of dialogue state."""

    def test_cannot_submit_without_name(self):
        e = InterviewEngine()
        e._merge_extracted({"직업": "미용사", "목표": "성장", "특기": "염색"})
        assert e.can_submit() is False
        assert "이름" in e.missing_for_submit()

    def test_cannot_submit_with_name_only(self):
        e = InterviewEngine()
        e._merge_extracted({"이름": "김민수"})
        assert e.can_submit() is False        # name alone < 4 required

    def test_can_submit_with_name_plus_four(self):
        e = InterviewEngine()
        e._merge_extracted(_SUBMITTABLE)
        assert e.can_submit() is True
        assert e.missing_for_submit() == []

    def test_reply_reports_can_submit(self):
        e = InterviewEngine(min_turns=1)
        with _patch(_resp(extracted=_SUBMITTABLE)):
            r = e.reply("정보 다 드릴게요")
        assert r.can_submit is True


class TestSummaryDoesNotEndDialogue:
    def test_summary_then_more_dialogue(self):
        """A summary is presentation only — user can keep talking."""
        e = InterviewEngine(min_turns=1)
        with _patch(_resp(rtype="summary", message="정리했습니다", sufficient=True,
                          extracted=_SUBMITTABLE)):
            r1 = e.reply("다 말씀드렸어요")
        assert r1.type == "summary"
        assert r1.sufficient is True
        assert e.confirmed is False           # NOT ended

        # user keeps talking -> still accepted (the #5 bug: this used to error)
        with _patch(_resp(message="추가로 메모할게요", extracted={"예산": "10만원"})):
            r2 = e.reply("아 예산도 있어요")
        assert r2.type == "question"
        assert e.extracted["예산"] == "10만원"

    def test_sufficient_requires_can_submit(self):
        """LLM says sufficient but data can't submit -> not a real summary."""
        e = InterviewEngine(min_turns=1)
        with _patch(_resp(rtype="summary", sufficient=True,
                          extracted={"직업": "미용사"})):  # no name
            r = e.reply("끝났어요")
        assert r.sufficient is False
        assert r.type == "question"


class TestConfirm:
    def test_confirm_true_ends_dialogue(self):
        e = InterviewEngine()
        e._merge_extracted(_SUBMITTABLE)
        d = e.confirm(True)
        assert isinstance(d, dict) and len(d) == 11
        assert e.confirmed is True

    def test_reply_after_confirm_is_rejected(self):
        e = InterviewEngine()
        e._merge_extracted(_SUBMITTABLE)
        e.confirm(True)
        r = e.reply("더 할 말 있어요")
        assert r.type == "error"

    def test_confirm_corrections_keeps_dialogue_open(self):
        e = InterviewEngine()
        d = e.confirm(False, {"이름": "김철수"})   # dict 경로 = LLM 미호출
        assert d["이름"] == "김철수"
        assert e.confirmed is False           # still open


class TestForceAndMinTurns:
    def test_force_extract_at_max_turns(self):
        """At max_turns the LLM is instructed to summarize; if submittable it ends as summary."""
        e = InterviewEngine(max_turns=1, min_turns=1)
        with _patch(_resp(rtype="summary", sufficient=True, extracted=_SUBMITTABLE)):
            r = e.reply("네")
        assert r.type == "summary"
        assert r.can_submit is True

    def test_min_turns_respected(self):
        e = InterviewEngine(min_turns=5)
        with _patch(_resp(rtype="summary", sufficient=True, extracted=_SUBMITTABLE)):
            r = e.reply("끝")  # turn 1 < min 5
        assert r.sufficient is False
        assert e.confirmed is False


class TestCompat:
    def test_refuse_field_marks_unknown(self):
        e = InterviewEngine()
        e._merge_extracted({"예산": "정보 없음"})
        assert e.get_subject()["예산"] == "정보 없음"

    def test_get_subject_compatibility(self):
        e = InterviewEngine()
        d = e.get_subject()
        for k in ["이름", "직업", "특기", "성격", "타겟연령대", "SNS경험", "목표"]:
            assert k in d

    def test_extended_fields_in_output(self):
        e = InterviewEngine()
        d = e.get_subject()
        for k in ["가용시간", "촬영환경", "카메라경험", "예산"]:
            assert k in d

    def test_conversation_save(self, tmp_path):
        e = InterviewEngine()
        with _patch([_resp(message="안녕하세요"), _resp(message="다음 질문")]):
            e.start()
            e.reply("김민수입니다")
        out = tmp_path / "conv.md"
        e.save_conversation(out)
        content = out.read_text(encoding="utf-8")
        assert "CEO" in content and "사용자" in content
