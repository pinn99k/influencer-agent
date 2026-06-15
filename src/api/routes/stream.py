import asyncio
import json
import queue

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter()

_session_mgr = None


def init_router(session_manager):
    global _session_mgr
    _session_mgr = session_manager


@router.get("/stream/{job_id}")
async def stream_events(job_id: str):
    job = _session_mgr.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    async def event_generator():
        while True:
            try:
                event = await asyncio.to_thread(job.sse_queue.get, timeout=30)
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
                if event.get("type") in ("job_completed", "job_failed", "cancelled"):
                    break
            except queue.Empty:
                yield ": keepalive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
