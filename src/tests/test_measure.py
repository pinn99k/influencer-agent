"""P1 tests — measurement/experiment layer (core/measure.py).

Spec: docs/workflow/2장_에이전트하네스/03_측정실험설계.md
  - weekly KPI records          -> .system/measure/kpi.md
  - per-content variable tagging -> .system/measure/content_log.md
  - decision log with provenance -> .system/measure/decision_log.md
  - weekly variable comparison (attribution baseline)

All disk tests clean up after themselves (no outputs/ pollution).
"""
import shutil

import pytest

from core.measure import (
    WeeklyKPI, ContentEntry, DecisionEntry, MeasureStore,
    ACTOR_AI, ACTOR_HUMAN,
)
from core.config import OUTPUTS_DIR

NAME = "테스트_측정"
BASE = OUTPUTS_DIR / NAME


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if BASE.exists():
        shutil.rmtree(BASE)


def _store():
    return MeasureStore(NAME)


# ---- weekly KPI ------------------------------------------------------------

def test_kpi_record_and_load_roundtrip():
    s = _store()
    s.record_kpi(WeeklyKPI(week=1, followers=120, content_count=3,
                           total_views=4500, engagement=210, conversions=0))
    kpis = s.load_kpis()
    assert len(kpis) == 1
    k = kpis[0]
    assert (k.week, k.followers, k.content_count) == (1, 120, 3)
    assert (k.total_views, k.engagement, k.conversions) == (4500, 210, 0)


def test_kpi_same_week_overwrites():
    s = _store()
    s.record_kpi(WeeklyKPI(week=1, followers=100))
    s.record_kpi(WeeklyKPI(week=1, followers=150))
    kpis = s.load_kpis()
    assert len(kpis) == 1
    assert kpis[0].followers == 150


def test_kpi_multiple_weeks_sorted():
    s = _store()
    s.record_kpi(WeeklyKPI(week=2, followers=200))
    s.record_kpi(WeeklyKPI(week=1, followers=100))
    assert [k.week for k in s.load_kpis()] == [1, 2]


def test_kpi_empty_when_no_file():
    assert _store().load_kpis() == []


# ---- per-content log (variable tagging) ------------------------------------

def _entry(**over):
    base = dict(date="2026-06-10", title="컬러 변신 꿀팁", topic="컬러",
                fmt="릴스", length="30초", time_slot="저녁",
                views=1200, likes=80, saves=15, comments=6, week=1)
    base.update(over)
    return ContentEntry(**base)


def test_content_log_append_and_load():
    s = _store()
    s.log_content(_entry())
    s.log_content(_entry(title="펌 기초", topic="펌", views=300))
    rows = s.load_contents()
    assert len(rows) == 2
    assert rows[0].topic == "컬러" and rows[0].views == 1200
    assert rows[1].topic == "펌" and rows[1].views == 300


def test_content_log_preserves_variable_tags():
    s = _store()
    s.log_content(_entry(fmt="쇼츠", length="15초", time_slot="점심"))
    r = s.load_contents()[0]
    assert (r.fmt, r.length, r.time_slot) == ("쇼츠", "15초", "점심")


def test_content_log_empty_when_no_file():
    assert _store().load_contents() == []


# ---- decision log + provenance ---------------------------------------------

def test_decision_log_records_provenance():
    s = _store()
    s.log_decision(DecisionEntry(actor=ACTOR_AI, basis="2주차 컬러 조회 급락",
                                 decision="컨셉기획 재실행"))
    s.log_decision(DecisionEntry(actor=ACTOR_HUMAN, basis="미용사 요청",
                                 decision="업로드 시간대 저녁으로 변경"))
    rows = s.load_decisions()
    assert len(rows) == 2
    assert rows[0].actor == ACTOR_AI
    assert rows[1].actor == ACTOR_HUMAN
    assert "컨셉기획" in rows[0].decision


def test_decision_log_rejects_unknown_actor():
    with pytest.raises(ValueError):
        DecisionEntry(actor="외계인", basis="x", decision="y")


def test_decision_log_counts_by_actor():
    s = _store()
    s.log_decision(DecisionEntry(actor=ACTOR_AI, basis="a", decision="d1"))
    s.log_decision(DecisionEntry(actor=ACTOR_AI, basis="b", decision="d2"))
    s.log_decision(DecisionEntry(actor=ACTOR_HUMAN, basis="c", decision="d3"))
    counts = s.decision_counts()
    assert counts[ACTOR_AI] == 2
    assert counts[ACTOR_HUMAN] == 1


def test_decision_log_empty_when_no_file():
    assert _store().load_decisions() == []


# ---- weekly variable comparison (attribution) -------------------------------

def test_compare_by_variable_topic():
    s = _store()
    s.log_content(_entry(topic="컬러", views=1000, likes=50, saves=10, comments=5))
    s.log_content(_entry(topic="컬러", views=2000, likes=100, saves=20, comments=10))
    s.log_content(_entry(topic="펌", views=300, likes=10, saves=2, comments=1))
    cmp = s.compare_by("topic")
    assert cmp["컬러"]["count"] == 2
    assert cmp["컬러"]["avg_views"] == 1500
    assert cmp["펌"]["count"] == 1
    assert cmp["펌"]["avg_views"] == 300
    # engagement = likes+saves+comments per item average
    assert cmp["컬러"]["avg_engagement"] == (65 + 130) / 2


def test_compare_by_rejects_unknown_variable():
    with pytest.raises(ValueError):
        _store().compare_by("없는변수")


def test_weekly_report_renders_korean_summary():
    s = _store()
    s.record_kpi(WeeklyKPI(week=1, followers=120, content_count=3, total_views=4500))
    s.log_content(_entry())
    s.log_decision(DecisionEntry(actor=ACTOR_AI, basis="x", decision="y"))
    report = s.weekly_report()
    assert "Week 1" in report or "1주차" in report
    assert "120" in report
