"""U5 API tests — server-session CEO chat route + direction persistence.

ASCII-only source. Fake chat engine avoids LLM. Direction endpoints reuse the
reanalyze router (cohesive with feedback/performance inputs).
"""
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import api.main as main_mod
from api.routes import chat as chat_mod
from core.chat_engine import ChatResponse
from core.config import OUTPUTS_DIR


class FakeChatEngine:
    def __init__(self, name):
        self.name = name
        self.turns = 0

    def start(self):
        return "greeting + direction question"

    def reply(self, message):
        self.turns += 1
        captured = "content: practice-video focus" if "practice" in message else ""
        return ChatResponse(f"reply {self.turns}", captured, self.turns * 2)


@pytest.fixture
def client():
    chat_mod.init_router(engine_factory=lambda name: FakeChatEngine(name))
    yield TestClient(main_mod.app)
    chat_mod.init_router(engine_factory=None)


def test_start_returns_id_and_greeting(client):
    res = client.post("/api/chat/start", json={"name": "Tester"})
    assert res.status_code == 200
    body = res.json()
    assert body["chat_id"]
    assert body["message"]


def test_reply_returns_message(client):
    cid = client.post("/api/chat/start", json={"name": "Tester"}).json()["chat_id"]
    res = client.post("/api/chat/reply", json={"chat_id": cid, "message": "hashtag tips?"})
    assert res.status_code == 200
    body = res.json()
    assert body["message"] == "reply 1"
    assert body["captured_direction"] == ""


def test_reply_captures_direction(client):
    cid = client.post("/api/chat/start", json={"name": "Tester"}).json()["chat_id"]
    res = client.post("/api/chat/reply",
                      json={"chat_id": cid, "message": "go practice video focus"})
    assert res.json()["captured_direction"] == "content: practice-video focus"


def test_reply_unknown_chat_404(client):
    res = client.post("/api/chat/reply", json={"chat_id": "nope", "message": "hi"})
    assert res.status_code == 404


def test_start_invalid_name_400(client):
    res = client.post("/api/chat/start", json={"name": "bad name!!"})
    assert res.status_code == 400


# ---- direction persistence (reanalyze router) ----------------------------

INFLUENCER = "테스트_chatapi"
BASE = OUTPUTS_DIR / INFLUENCER


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if BASE.exists():
        shutil.rmtree(BASE)


def test_direction_put_then_get(client):
    put = client.put(f"/api/direction/{INFLUENCER}", json={"content": "# 방향\n연습영상 위주"})
    assert put.status_code == 200
    got = client.get(f"/api/direction/{INFLUENCER}")
    assert got.status_code == 200
    assert "연습영상 위주" in got.json()["content"]


def test_direction_get_none_when_absent(client):
    got = client.get(f"/api/direction/{INFLUENCER}")
    assert got.status_code == 200
    assert got.json()["content"] is None
