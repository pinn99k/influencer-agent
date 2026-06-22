"""API tests for the server-session interview route (V2 Spiral 5-E, refactored).

Dialogue and submission are separated:
- /reply exposes can_submit
- /confirm gates on can_submit; a non-submittable confirm returns 200 with
  approved=False + missing (dialogue stays alive), NOT a 400.

ASCII-only: Korean field keys imported as constants. Fake engine avoids LLM.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api.main as main_mod
from api.routes import interview as interview_mod
from api.routes.interview import _NAME_KEY, _GOAL_KEY
from core.interview_engine import InterviewResponse


class FakeEngine:
    """Deterministic stand-in for InterviewEngine (no LLM)."""

    def __init__(self):
        self.turn = 0
        self.confirmed = False
        self._submittable = False
        self._subject = {_NAME_KEY: "정보 없음", _GOAL_KEY: "정보 없음"}

    def start(self):
        return "greeting + first question"

    def can_submit(self):
        return self._submittable

    def missing_for_submit(self):
        return [] if self._submittable else [_NAME_KEY]

    def get_subject(self):
        return dict(self._subject)

    def reply(self, message):
        self.turn += 1
        if self.turn >= 2:
            # second turn: enough info -> submittable
            self._submittable = True
            self._subject = {_NAME_KEY: "Tester", _GOAL_KEY: "grow to 500"}
            return InterviewResponse(
                "summary", "here is the summary",
                dict(self._subject), True, self.turn, True,
            )
        return InterviewResponse(
            "question", "next question", {}, False, self.turn, False,
        )

    def confirm(self, approved, corrections=None):
        if approved:
            self.confirmed = True
        return dict(self._subject)


@pytest.fixture
def client(monkeypatch):
    interview_mod.init_router(main_mod.session_mgr, engine_factory=FakeEngine)
    monkeypatch.setattr(main_mod.session_mgr, "start_job", lambda subject, mode="linear": "fakejob123")
    yield TestClient(main_mod.app)
    interview_mod.init_router(main_mod.session_mgr, engine_factory=None)


def test_start_returns_id_and_greeting(client):
    res = client.post("/api/interview/start")
    assert res.status_code == 200
    body = res.json()
    assert body["interview_id"]
    assert body["type"] == "question"
    assert body["message"]


def test_reply_progresses_to_summary_and_can_submit(client):
    iid = client.post("/api/interview/start").json()["interview_id"]

    r1 = client.post("/api/interview/reply",
                     json={"interview_id": iid, "message": "I am a hairdresser"})
    assert r1.status_code == 200
    assert r1.json()["type"] == "question"
    assert r1.json()["turn_count"] == 1
    assert r1.json()["can_submit"] is False

    r2 = client.post("/api/interview/reply",
                     json={"interview_id": iid, "message": "more details"})
    assert r2.json()["type"] == "summary"
    assert r2.json()["sufficient"] is True
    assert r2.json()["can_submit"] is True
    assert r2.json()["extracted"][_NAME_KEY] == "Tester"


def test_confirm_starts_job_when_submittable(client):
    iid = client.post("/api/interview/start").json()["interview_id"]
    # make it submittable (2 replies)
    client.post("/api/interview/reply", json={"interview_id": iid, "message": "a"})
    client.post("/api/interview/reply", json={"interview_id": iid, "message": "b"})

    res = client.post("/api/interview/confirm",
                      json={"interview_id": iid, "approved": True})
    assert res.status_code == 200
    body = res.json()
    assert body["job_id"] == "fakejob123"
    assert body["subject"][_NAME_KEY] == "Tester"
    # engine cleaned up after successful start
    follow = client.post("/api/interview/reply",
                         json={"interview_id": iid, "message": "x"})
    assert follow.status_code == 404


def test_confirm_not_submittable_keeps_dialogue(client):
    """The #5 fix: confirming too early returns 200 + missing, dialogue survives."""
    iid = client.post("/api/interview/start").json()["interview_id"]
    # only 1 reply -> not submittable yet
    client.post("/api/interview/reply", json={"interview_id": iid, "message": "a"})

    res = client.post("/api/interview/confirm",
                      json={"interview_id": iid, "approved": True})
    assert res.status_code == 200
    body = res.json()
    assert body["approved"] is False
    assert body["can_submit"] is False
    assert _NAME_KEY in body["missing"]
    assert "job_id" not in body

    # dialogue still alive -> a further reply is accepted (not 404)
    follow = client.post("/api/interview/reply",
                         json={"interview_id": iid, "message": "more"})
    assert follow.status_code == 200


def test_confirm_without_start(client):
    iid = client.post("/api/interview/start").json()["interview_id"]
    client.post("/api/interview/reply", json={"interview_id": iid, "message": "a"})
    client.post("/api/interview/reply", json={"interview_id": iid, "message": "b"})
    res = client.post("/api/interview/confirm",
                      json={"interview_id": iid, "approved": True, "start_job": False})
    assert res.status_code == 200
    assert "job_id" not in res.json()


def test_reply_unknown_interview_404(client):
    res = client.post("/api/interview/reply",
                      json={"interview_id": "nope", "message": "hi"})
    assert res.status_code == 404
