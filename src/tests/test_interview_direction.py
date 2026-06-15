"""U3 tests — interview direction capture + persistence on confirm.

The interview now also collects a DirectionProfile (content focus / target goal /
strategy focus). Direction fields live alongside subject fields in `extracted`
but never leak into get_subject(); on a submittable confirm they are saved to
방향.md so CEO.run() reflects them.
"""
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.interview_engine import (
    InterviewEngine, _DIRECTION_FIELDS, _PLACEHOLDER,
)
from core.config import OUTPUTS_DIR


# ---- engine-level: direction extraction (no LLM) -------------------------

def test_direction_fields_present_in_extracted():
    eng = InterviewEngine()
    for f in _DIRECTION_FIELDS:
        assert f in eng.extracted


def test_get_subject_excludes_direction_fields():
    eng = InterviewEngine()
    subj = eng.get_subject()
    for f in _DIRECTION_FIELDS:
        assert f not in subj


def test_get_direction_maps_fields():
    eng = InterviewEngine()
    eng.extracted["콘텐츠방향"] = "연습영상 위주"
    eng.extracted["핵심목표"] = "팔로워 100만"
    eng.extracted["중점전략"] = "프로필 꾸미기, 해시태그"
    d = eng.get_direction()
    assert d.content_focus == "연습영상 위주"
    assert d.target_goal == "팔로워 100만"
    assert d.strategy_focus == ["프로필 꾸미기", "해시태그"]


def test_get_direction_empty_when_placeholders():
    assert InterviewEngine().get_direction().is_empty()


def test_direction_field_is_mergeable():
    eng = InterviewEngine()
    eng._merge_extracted({"콘텐츠방향": "시술 비포애프터"})
    assert eng.extracted["콘텐츠방향"] == "시술 비포애프터"


# ---- route-level: direction saved on confirm -----------------------------

import api.main as main_mod  # noqa: E402
from api.routes import interview as interview_mod  # noqa: E402
from api.routes.interview import _NAME_KEY, _GOAL_KEY  # noqa: E402
from core.direction import DirectionProfile  # noqa: E402
from core.interview_engine import InterviewResponse  # noqa: E402

DIR_NAME = "DirTester"
DIR_BASE = OUTPUTS_DIR / DIR_NAME


class FakeEngineWithDirection:
    def __init__(self):
        self.confirmed = False

    def start(self):
        return "hi"

    def can_submit(self):
        return True

    def missing_for_submit(self):
        return []

    def get_subject(self):
        return {_NAME_KEY: DIR_NAME, _GOAL_KEY: "grow"}

    def reply(self, message):
        return InterviewResponse("summary", "ok", self.get_subject(), True, 1, True)

    def confirm(self, approved, corrections=None):
        self.confirmed = True
        return self.get_subject()

    def get_direction(self):
        return DirectionProfile(content_focus="practice video focus")


@pytest.fixture
def client(monkeypatch):
    interview_mod.init_router(main_mod.session_mgr, engine_factory=FakeEngineWithDirection)
    monkeypatch.setattr(main_mod.session_mgr, "start_job", lambda subject: "fakejob")
    yield TestClient(main_mod.app)
    interview_mod.init_router(main_mod.session_mgr, engine_factory=None)
    if DIR_BASE.exists():
        shutil.rmtree(DIR_BASE)


def test_confirm_saves_direction_md(client):
    iid = client.post("/api/interview/start").json()["interview_id"]
    res = client.post("/api/interview/confirm", json={"interview_id": iid, "approved": True})
    assert res.status_code == 200
    assert res.json()["job_id"] == "fakejob"
    saved = DIR_BASE / "방향.md"
    assert saved.exists()
    assert "practice video focus" in saved.read_text(encoding="utf-8")
