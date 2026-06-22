from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from core.config import OUTPUTS_DIR

router = APIRouter()

_session_mgr = None


def init_router(session_manager):
    global _session_mgr
    _session_mgr = session_manager


class StartRequest(BaseModel):
    subject: dict
    mode: str = "linear"  # "linear" | "autonomous" (2장 자율 도구 루프)

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v):
        for key in ("이름", "목표"):
            val = v.get(key, "")
            if not val or not str(val).strip():
                raise ValueError(f"Required field missing: {key}")
        return v


@router.post("/start")
async def start_run(request: StartRequest):
    mode = request.mode if request.mode in ("linear", "autonomous") else "linear"
    try:
        job_id = _session_mgr.start_job(request.subject, mode=mode)
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    return {"job_id": job_id, "status": "started", "mode": mode}


@router.get("/status")
async def get_all_status():
    return {"jobs": _session_mgr.get_all_jobs()}


@router.get("/agent-output/{job_id}/{agent_key}")
async def get_agent_output(job_id: str, agent_key: str):
    valid_agents = ["대상분석", "경쟁분석", "플랫폼추천", "컨셉기획"]
    if agent_key not in valid_agents:
        raise HTTPException(status_code=400, detail=f"Invalid agent key: {agent_key}")

    # Resolve influencer name: prefer the live job, but fall back to treating the
    # path segment as an influencer name so disk-stored outputs stay reachable after
    # a server restart kills the in-memory job (Fix B).
    job = _session_mgr.get_job(job_id)
    name = job.influencer_name if job else job_id

    raw_path = OUTPUTS_DIR / name / ".system" / "agents" / agent_key / "raw_output.md"
    if not raw_path.exists():
        raise HTTPException(status_code=404, detail="Agent output not found")

    content = raw_path.read_text(encoding="utf-8")
    return {"agent": agent_key, "content": content}


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    job = _session_mgr.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    # Collect available reports
    reports = []
    deliverables_dir = OUTPUTS_DIR / job.influencer_name / "산출물"
    if deliverables_dir.exists():
        reports = sorted(
            f.name for f in deliverables_dir.iterdir()
            if f.is_file() and f.suffix == ".md"
        )

    # Collect recent events for page-reload recovery
    recent_events = []
    if job.emitter:
        recent_events = job.emitter.get_recent_events(20)

    return {
        "job_id": job.job_id,
        "influencer_name": job.influencer_name,
        "status": job.status,
        "error": job.error,
        "subject": job.subject,
        "reports": reports,
        "recent_events": recent_events,
    }
