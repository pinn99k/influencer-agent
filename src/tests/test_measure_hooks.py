"""P1-U3/U4 tests — decision-log hooks (provenance) + measure API.

Hooks under test:
  - AI:    CEO.run_reanalyze logs its rerun decision (actor=AI)
  - human: PUT /api/direction logs the user's direction change (actor=사람)
  - human: POST /api/reanalyze logs the reanalysis trigger (actor=사람)

API under test (routes/measure.py):
  - PUT  /api/measure/{name}/kpi
  - POST /api/measure/{name}/content
  - GET  /api/measure/{name}/summary
"""
import shutil
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import api.main as main_mod
from core.measure import MeasureStore, ACTOR_AI, ACTOR_HUMAN
from core.config import OUTPUTS_DIR

NAME = "테스트_측정훅"
BASE = OUTPUTS_DIR / NAME


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if BASE.exists():
        shutil.rmtree(BASE)


# ---- AI hook: CEO rerun decision -------------------------------------------

def test_ceo_rerun_decision_logged_with_ai_provenance():
    from agents.ceo import CEO
    fm = MagicMock()
    fm.name = NAME
    fm.load_existing_outputs.return_value = {}
    fm.load_performance_record.return_value = "Week1 팔로워 100"
    fm.load_feedback.return_value = "컨셉 B로 바꿔줘"
    fm.load_direction.return_value = None

    ceo = CEO(fm, dry_run=True)   # dry_run: stop after the decision phase
    with patch.object(ceo, "_decide_rerun", return_value=[]):
        ceo.run_reanalyze({"대상자": {"이름": NAME}})

    decisions = MeasureStore(NAME).load_decisions()
    assert len(decisions) == 1
    assert decisions[0].actor == ACTOR_AI


# ---- human hooks + API -------------------------------------------------------

@pytest.fixture
def client():
    return TestClient(main_mod.app)


def test_direction_put_logs_human_decision(client):
    client.put(f"/api/direction/{NAME}", json={"content": "# 방향\n연습영상 위주"})
    decisions = MeasureStore(NAME).load_decisions()
    assert len(decisions) == 1
    assert decisions[0].actor == ACTOR_HUMAN
    assert "연습영상" in decisions[0].decision


def test_measure_kpi_put_and_summary(client):
    r = client.put(f"/api/measure/{NAME}/kpi",
                   json={"week": 1, "followers": 130, "content_count": 3,
                         "total_views": 5000, "engagement": 250, "conversions": 1})
    assert r.status_code == 200
    s = client.get(f"/api/measure/{NAME}/summary")
    assert s.status_code == 200
    assert "130" in s.json()["summary"]


def test_measure_content_post_and_compare(client):
    r = client.post(f"/api/measure/{NAME}/content",
                    json={"date": "2026-06-10", "week": 1, "title": "컬러 꿀팁",
                          "topic": "컬러", "fmt": "릴스", "length": "30초",
                          "time_slot": "저녁", "views": 1200, "likes": 80,
                          "saves": 15, "comments": 6})
    assert r.status_code == 200
    rows = MeasureStore(NAME).load_contents()
    assert len(rows) == 1 and rows[0].topic == "컬러"


def test_measure_summary_empty_ok(client):
    s = client.get(f"/api/measure/{NAME}/summary")
    assert s.status_code == 200
    assert s.json()["summary"]
