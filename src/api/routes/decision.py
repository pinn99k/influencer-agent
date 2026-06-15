from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_session_mgr = None


def init_router(session_manager):
    global _session_mgr
    _session_mgr = session_manager


class DecisionRequest(BaseModel):
    choice: str
    reason: str = ""


@router.post("/decision/{job_id}")
async def submit_decision(job_id: str, request: DecisionRequest):
    try:
        _session_mgr.submit_decision(job_id, request.choice, request.reason)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "decision_submitted", "choice": request.choice}


@router.delete("/job/{job_id}")
async def cancel_job(job_id: str):
    try:
        _session_mgr.cancel_job(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return {"status": "cancelled", "job_id": job_id}
