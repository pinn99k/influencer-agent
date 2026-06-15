"""Interview route -- server-side session for the conversational intake (V2 Spiral 5-E).

The InterviewEngine is stateful (multi-turn). We keep one engine instance per
interview_id in a module-level registry so the chat UI can call /reply each turn.

This module intentionally contains NO Korean literals (see .claude/lessons.md):
field keys are imported from core.interview_engine.
"""
import threading
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.interview_engine import InterviewEngine, _REQUIRED_FIELDS
from core.file_manager import FileManager

router = APIRouter()

_NAME_KEY = _REQUIRED_FIELDS[0]   # "이름"
_GOAL_KEY = _REQUIRED_FIELDS[-1]  # "목표"


def _save_direction_if_any(engine, subject: dict) -> None:
    """On a submittable confirm, persist the user-chosen direction so CEO.run()
    reflects it. No-op when the engine exposes no direction or it is empty.
    Korean lives only in DirectionProfile.to_markdown / FileManager (route stays
    ASCII-only)."""
    get_dir = getattr(engine, "get_direction", None)
    if get_dir is None:
        return
    direction = get_dir()
    if direction.is_empty():
        return
    name = (subject.get(_NAME_KEY) or "").strip()
    if name and name != _PLACEHOLDER:
        FileManager(name).save_direction(direction.to_markdown(name))
_PLACEHOLDER = "정보 없음"

_session_mgr = None
_engine_factory = InterviewEngine
_engines: dict = {}
_lock = threading.Lock()


def init_router(session_manager, engine_factory=None):
    """Wire the CEO session manager and (optionally) a custom engine factory.

    Tests pass a fake factory to avoid real LLM calls.
    """
    global _session_mgr, _engine_factory
    _session_mgr = session_manager
    if engine_factory is not None:
        _engine_factory = engine_factory


def _get(interview_id: str):
    engine = _engines.get(interview_id)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Interview not found: {interview_id}")
    return engine


@router.post("/interview/start")
async def interview_start():
    interview_id = uuid.uuid4().hex[:12]
    engine = _engine_factory()
    greeting = engine.start()
    with _lock:
        _engines[interview_id] = engine
    return {
        "interview_id": interview_id,
        "type": "question",
        "message": greeting,
        "turn_count": 0,
    }


class ReplyRequest(BaseModel):
    interview_id: str
    message: str


@router.post("/interview/reply")
async def interview_reply(req: ReplyRequest):
    engine = _get(req.interview_id)
    resp = engine.reply(req.message)
    return {
        "type": resp.type,
        "message": resp.message,
        "extracted": resp.extracted,
        "sufficient": resp.sufficient,
        "turn_count": resp.turn_count,
        "can_submit": resp.can_submit,
    }


class ConfirmRequest(BaseModel):
    interview_id: str
    approved: bool = True
    corrections: dict | None = None
    start_job: bool = True


@router.post("/interview/confirm")
async def interview_confirm(req: ConfirmRequest):
    engine = _get(req.interview_id)

    # Submission gate (independent of dialogue): only block the actual job start.
    # A non-submittable confirm must NOT end the dialogue — the user can keep
    # talking and try again (this is the #5 fix: dialogue/submit separation).
    if req.approved and req.start_job and not engine.can_submit():
        return {
            "subject": engine.get_subject(),
            "approved": False,
            "can_submit": False,
            "missing": engine.missing_for_submit(),
        }

    subject = engine.confirm(req.approved, req.corrections)
    result = {"subject": subject, "approved": req.approved,
              "can_submit": engine.can_submit()}

    # On approval, hand the collected subject straight to the CEO pipeline.
    if req.approved and req.start_job:
        # Persist the user-chosen direction before the pipeline runs so the very
        # first analysis already reflects it (U3).
        _save_direction_if_any(engine, subject)
        try:
            job_id = _session_mgr.start_job(subject)
        except RuntimeError as e:
            raise HTTPException(status_code=429, detail=str(e))
        result["job_id"] = job_id
        with _lock:
            _engines.pop(req.interview_id, None)

    return result
