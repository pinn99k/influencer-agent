"""Track-0 V-3/V-4: supervisory-layer verification (no LLM).

V-3: ManagerAgent deterministic accuracy — generate_weekly_card(cal, N) must
     extract EXACTLY week N, not bleed adjacent weeks. (Manager uses no LLM, so
     'quality' = extraction/format correctness, not a 0-100 score.)

V-4: Chairman-report condition coverage — documents which of the 10 conditions
     actually fire on the live CEO.run() path. This is a GAP RECORD: the test
     asserts the known-implemented condition (9) and pins the known gaps so a
     future change that wires more conditions will visibly update these tests.

Korean here is pure Hangul (display strings the manager emits); CJK self-checked.
"""
from unittest.mock import MagicMock

import pytest

from agents.manager import ManagerAgent
import agents.ceo as ceo_mod


# ── V-3: manager deterministic week extraction ───────────────────────────────
_FOUR_WEEKS = """### 4주 콘텐츠 캘린더
#### Week 1 (난이도: 입문)
1. **W1 첫영상** — 쇼츠 / 인사
2. **W1 도구** — 쇼츠 / 준비물
#### Week 2 (난이도: 기초)
1. **W2 비포애프터** — 쇼츠 / 변화
2. **W2 큐엔에이** — 쇼츠 / 소통
#### Week 3 (난이도: 중급)
1. **W3 트렌드** — 쇼츠 / 정보
2. **W3 협업** — 쇼츠 / 콜라보
#### Week 4 (난이도: 심화)
1. **W4 시리즈** — 쇼츠 / 기획
2. **W4 마무리** — 쇼츠 / 정리
### 촬영 실행 가이드
- 장비: 스마트폰
"""


def _mgr():
    return ManagerAgent(MagicMock(), event_emitter=None)


@pytest.mark.parametrize("week,want,absent", [
    (1, "W1 첫영상", "W2 비포애프터"),
    (2, "W2 비포애프터", "W3 트렌드"),
    (3, "W3 트렌드", "W4 시리즈"),
    (4, "W4 시리즈", "촬영 실행 가이드"),  # must not bleed into the next section
])
def test_weekly_card_extracts_exact_week(week, want, absent):
    card = _mgr().generate_weekly_card(_FOUR_WEEKS, week)
    assert want in card, f"week {week} should contain its own item"
    assert absent not in card, f"week {week} card bled into '{absent}'"


def test_weekly_card_week4_stops_before_guide():
    """Week 4 is the last week — extraction must stop at the next '###' section."""
    card = _mgr().generate_weekly_card(_FOUR_WEEKS, 4)
    assert "W4 시리즈" in card and "W4 마무리" in card
    assert "장비: 스마트폰" not in card


def test_progress_report_reflects_validation():
    """progress_report must mark only agents present in agent_results."""
    m = _mgr()
    agent_results = {"대상_분석": "x", "경쟁_분석": "y"}
    validation = {"대상분석": {"passed": True, "quality_score": 88},
                  "경쟁분석": {"passed": False}}
    report = m.generate_progress_report(agent_results, validation)
    assert "대상분석: 완료 (품질 88/100)" in report
    assert "경쟁분석: 완료 (검증 미통과)" in report
    assert "플랫폼추천: 대기중" in report   # not in agent_results
    assert "컨셉기획: 대기중" in report


# ── V-4: chairman-report condition coverage (GAP RECORD) ─────────────────────
def test_auto_conditions_constant():
    """Code auto-detects only conditions 5 (2x fail) and 9 (execution handoff)."""
    assert ceo_mod.AUTO_CONDITIONS == {5, 9}


def test_llm_conditions_constant_is_narrow():
    """Spec lists 10 conditions; code's LLM-judged set is only {3, 6}.

    GAP: conditions 1,2,4,7,8,10 have NO active firing point in CEO.run().
    This test pins that fact. If a future change wires more conditions, update
    this assertion deliberately (it should not change silently).
    """
    assert ceo_mod.LLM_CONDITIONS == {3, 6}


def test_condition9_is_the_only_guaranteed_fire():
    """On the live path, _finalize -> _request_approval -> _report_to_chairman(9).

    Conditions 3/6 depend on _check_llm_chairman_conditions which is NOT called
    in _agent_loop (dead code on the live path — _check_briefing_for_chairman is
    used instead). So condition 9 is the only guaranteed chairman trigger today.
    This is the documented gap for Track-0 V-4.
    """
    src = __import__("inspect").getsource(ceo_mod.CEO._agent_loop)
    assert "_check_llm_chairman_conditions" not in src, \
        "if this method is now wired into _agent_loop, V-4 gap is closing — update the record"
    assert "_check_briefing_for_chairman" in src
