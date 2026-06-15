"""Chat route -- server-side session for the context-aware CEO chat (U5).

ChatEngine is stateful (multiturn); one instance is kept per chat_id in a
module-level registry so the UI can call /reply each turn.

ASCII-only source (see .claude/lessons.md): no Korean literals. Influencer name
validation uses \\w, which matches Unicode (Hangul) letters.
"""
import re
import threading
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.chat_engine import ChatEngine
from core.file_manager import FileManager

router = APIRouter()

_SAFE_NAME = re.compile(r"^[\w-]+$")
_engines: dict = {}
_lock = threading.Lock()


def _default_factory(name: str):
    return ChatEngine(FileManager(name))


_engine_factory = _default_factory


def init_router(engine_factory=None):
    """Wire an engine factory. Tests pass a fake to avoid real LLM calls."""
    global _engine_factory
    _engine_factory = engine_factory or _default_factory


def _validate_name(name: str) -> str:
    if not name or not _SAFE_NAME.match(name):
        raise HTTPException(status_code=400, detail="Invalid influencer name")
    return name


def _get(chat_id: str):
    engine = _engines.get(chat_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Chat not found: {chat_id}")
    return engine


class StartRequest(BaseModel):
    name: str


@router.post("/chat/start")
async def chat_start(req: StartRequest):
    name = _validate_name(req.name)
    chat_id = uuid.uuid4().hex[:12]
    engine = _engine_factory(name)
    greeting = engine.start()
    with _lock:
        _engines[chat_id] = engine
    return {"chat_id": chat_id, "message": greeting}


class ReplyRequest(BaseModel):
    chat_id: str
    message: str


@router.post("/chat/reply")
async def chat_reply(req: ReplyRequest):
    engine = _get(req.chat_id)
    r = engine.reply(req.message)
    return {"message": r.message, "captured_direction": r.captured_direction}


@router.get("/chat/history/{name}")
async def chat_history(name: str):
    """Persisted conversation for boot recovery (survives server restarts)."""
    name = _validate_name(name)
    return {"name": name, "messages": FileManager(name).load_chat_history()}
