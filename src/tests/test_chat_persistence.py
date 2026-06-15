"""P2 tests — CEO chat history persistence (.system/chat_history.jsonl).

Chat used to live only in memory: a page refresh or server restart lost the
whole conversation. Now FileManager persists each turn and ChatEngine restores
its history on construction, and the frontend can rehydrate via GET /chat/history.
"""
import shutil
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import api.main as main_mod
from core.chat_engine import ChatEngine
from core.file_manager import FileManager
from core.config import OUTPUTS_DIR

NAME = "테스트_채팅영속"
BASE = OUTPUTS_DIR / NAME


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if BASE.exists():
        shutil.rmtree(BASE)


# ---- FileManager layer ------------------------------------------------------

def test_append_and_load_roundtrip():
    fm = FileManager(NAME)
    fm.append_chat_message("user", "해시태그 전략 알려줘")
    fm.append_chat_message("assistant", "이렇게 하세요")
    history = fm.load_chat_history()
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "해시태그 전략 알려줘"}
    assert history[1]["role"] == "assistant"


def test_load_empty_when_no_file():
    assert FileManager(NAME).load_chat_history() == []


def test_multiline_content_survives():
    fm = FileManager(NAME)
    fm.append_chat_message("assistant", "첫 줄\n둘째 줄")
    assert fm.load_chat_history()[0]["content"] == "첫 줄\n둘째 줄"


# ---- ChatEngine integration --------------------------------------------------

def test_engine_persists_turns_to_disk():
    fm = FileManager(NAME)
    eng = ChatEngine(fm)
    with patch("core.chat_engine.call_llm_messages", return_value='{"message": "답변"}'):
        eng.reply("질문")
    history = fm.load_chat_history()
    assert [m["role"] for m in history] == ["user", "assistant"]


def test_new_engine_restores_history():
    fm = FileManager(NAME)
    first = ChatEngine(fm)
    with patch("core.chat_engine.call_llm_messages", return_value='{"message": "답1"}'):
        first.reply("질문1")

    # simulate server restart: brand-new engine, same influencer
    second = ChatEngine(FileManager(NAME))
    assert len(second.history) == 2
    assert second.history[0]["content"] == "질문1"


# ---- API: GET /chat/history/{name} -------------------------------------------

def test_history_endpoint_returns_messages():
    fm = FileManager(NAME)
    fm.append_chat_message("user", "안녕")
    fm.append_chat_message("assistant", "반가워요")
    client = TestClient(main_mod.app)
    r = client.get(f"/api/chat/history/{NAME}")
    assert r.status_code == 200
    msgs = r.json()["messages"]
    assert len(msgs) == 2 and msgs[1]["content"] == "반가워요"


def test_history_endpoint_empty_ok():
    client = TestClient(main_mod.app)
    r = client.get(f"/api/chat/history/{NAME}")
    assert r.status_code == 200
    assert r.json()["messages"] == []
