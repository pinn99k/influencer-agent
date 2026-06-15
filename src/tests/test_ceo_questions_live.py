"""Track-0 V-2 (live): real-LLM verification of CEO question routing.

Existing test_ceo_questions.py mocks call_llm, so it only proves PLUMBING, not
that the CEO's 3-way classifier actually works. This opt-in test calls the real
LLM with deliberately ambiguous agent questions and checks the routing is sane.

Skipped automatically when OPENAI_API_KEY is absent (CI / offline).
Run explicitly:  python -m pytest tests/test_ceo_questions_live.py -q
"""
import os

import pytest

from agents.ceo import CEO

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="real-LLM test; needs OPENAI_API_KEY",
)


class _FM:
    """Minimal FileManager stub (question handling does no file I/O)."""
    def load_performance_record(self):
        return None


def _ceo():
    c = CEO(_FM(), dry_run=False)
    return c


def test_question_routing_real_llm():
    """One question of each kind should route to the right bucket."""
    c = _ceo()
    ctx = {
        "대상자": {
            "이름": "최유나", "직업": "미용사", "특기": "염색 전문",
            "타겟연령대": "20대 여성", "목표": "유튜브 구독자 1000명",
            # 성격 intentionally omitted -> DATA question should detect it missing
        },
        "에이전트_질문": {
            "대상분석": [
                "타겟을 20대 남성으로 바꿔야 할까요?",      # STRATEGIC -> escalate
                "성격이 내향적인가요 외향적인가요?",          # DATA (missing) -> data_request or null
            ],
            "컨셉기획": [
                "컨셉 3개 중 염색 위주로 좁혀도 될까요?",      # TACTICAL -> CEO answers
            ],
        },
    }
    c._handle_agent_questions(ctx)
    r = ctx["질문_응답"]

    # The classifier fired (not the all-escalate fallback): at least one TACTICAL
    # answer OR the strategic one escalated. We assert structural sanity, not exact
    # wording (LLM nondeterminism).
    total = len(r["answers"]) + len(r["escalated"]) + len(r["data_requests"])
    assert total == 3, f"every question must be classified exactly once, got {r}"

    # The strategy-change question should not be silently answered as tactical.
    strat_q = "타겟을 20대 남성으로 바꿔야 할까요?"
    assert strat_q in r["escalated"] or strat_q not in r["answers"], \
        f"strategic question mishandled: {r}"

    # Not the blanket-fallback (which would escalate ALL three).
    assert len(r["escalated"]) < 3, f"looks like fallback fired: {r}"
