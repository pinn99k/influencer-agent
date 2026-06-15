import threading
import queue
import uuid
from dataclasses import dataclass, field
from typing import Optional

from core.file_manager import FileManager
from core.config import MAX_CONCURRENT_JOBS
from agents.ceo import CEO
from agents import get_context_keys
from api.event_emitter import EventEmitter


@dataclass
class JobContext:
    job_id: str
    influencer_name: str
    subject: dict
    sse_queue: queue.Queue = field(default_factory=queue.Queue)
    decision_event: threading.Event = field(default_factory=threading.Event)
    decision_store: dict = field(default_factory=dict)
    thread: Optional[threading.Thread] = None
    status: str = "pending"
    error: Optional[str] = None
    emitter: Optional[EventEmitter] = None


class SessionManager:
    """Owns CEO job lifecycle: create, run in thread, track, decision gate."""

    def __init__(self):
        self._jobs: dict[str, JobContext] = {}
        self._lock = threading.Lock()

    def start_job(self, subject: dict) -> str:
        with self._lock:
            running = sum(1 for j in self._jobs.values() if j.status == "running")
            if running >= MAX_CONCURRENT_JOBS:
                raise RuntimeError(f"Max concurrent jobs ({MAX_CONCURRENT_JOBS}) reached")

        job_id = uuid.uuid4().hex[:12]
        name = subject.get("이름", "unknown")
        job = JobContext(job_id=job_id, influencer_name=name, subject=subject)

        t = threading.Thread(target=self._run_ceo, args=(job,), daemon=True)
        job.thread = t

        with self._lock:
            self._jobs[job_id] = job

        t.start()
        return job_id

    def get_job(self, job_id: str) -> Optional[JobContext]:
        return self._jobs.get(job_id)

    def get_all_jobs(self) -> list[dict]:
        return [
            {
                "job_id": j.job_id,
                "influencer_name": j.influencer_name,
                "status": j.status,
                "error": j.error,
            }
            for j in self._jobs.values()
        ]

    def submit_decision(self, job_id: str, choice: str, reason: str = "") -> None:
        job = self._jobs.get(job_id)
        if not job:
            raise KeyError(f"Job not found: {job_id}")
        if job.status != "waiting_decision":
            raise ValueError(f"Job {job_id} not waiting for decision (status: {job.status})")
        job.decision_store["decision"] = {"choice": choice, "reason": reason}
        job.decision_event.set()
        job.status = "running"

    def cancel_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            raise KeyError(f"Job not found: {job_id}")
        job.status = "cancelled"
        job.decision_event.set()

    def _run_ceo(self, job: JobContext) -> None:
        job.status = "running"
        try:
            fm = FileManager(job.influencer_name)
            emitter = EventEmitter(
                fm, job.sse_queue, job.decision_event, job.decision_store,
                job_context=job,
            )
            job.emitter = emitter
            emitter.emit("job_started", {
                "job_id": job.job_id, "influencer": job.influencer_name,
            })

            context = self._init_context(job.subject)
            ceo = CEO(fm, dry_run=False, event_emitter=emitter)
            ceo.run(context)

            job.status = "completed"
            emitter.emit("job_completed", {"job_id": job.job_id})
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            try:
                emitter_fb = EventEmitter(
                    FileManager(job.influencer_name),
                    job.sse_queue, job.decision_event, job.decision_store,
                )
                emitter_fb.emit("job_failed", {"job_id": job.job_id, "error": str(e)})
            except Exception:
                pass

    def start_reanalyze_job(self, name: str, feedback: str | None = None) -> str:
        """재분석 잡 시작. 기존 outputs/{name} 기반."""
        with self._lock:
            running = sum(1 for j in self._jobs.values() if j.status == "running")
            if running >= MAX_CONCURRENT_JOBS:
                raise RuntimeError(f"Max concurrent jobs ({MAX_CONCURRENT_JOBS}) reached")

        job_id = uuid.uuid4().hex[:12]
        subject = {"이름": name}  # 최소 subject — CEO가 기존 산출물에서 복원
        job = JobContext(job_id=job_id, influencer_name=name, subject=subject)

        t = threading.Thread(
            target=self._run_ceo_reanalyze,
            args=(job, feedback),
            daemon=True,
        )
        job.thread = t

        with self._lock:
            self._jobs[job_id] = job

        t.start()
        return job_id

    def _run_ceo_reanalyze(self, job: JobContext, feedback: str | None = None) -> None:
        job.status = "running"
        try:
            fm = FileManager(job.influencer_name)

            # 피드백 저장 (API에서 직접 전달된 경우)
            if feedback:
                fm.save_feedback(feedback)

            emitter = EventEmitter(
                fm, job.sse_queue, job.decision_event, job.decision_store,
                job_context=job,
            )
            job.emitter = emitter
            emitter.emit("job_started", {
                "job_id": job.job_id,
                "influencer": job.influencer_name,
                "mode": "reanalyze",
            })

            context = self._init_context(job.subject)
            ceo = CEO(fm, dry_run=False, event_emitter=emitter)
            ceo.run_reanalyze(context)

            job.status = "completed"
            # mode lets the UI distinguish a reanalysis from a first analysis
            # instead of hardcoding "1차 분석을 마쳤어요" (CEO message <-> backend).
            emitter.emit("job_completed", {"job_id": job.job_id, "mode": "reanalyze"})
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            try:
                emitter_fb = EventEmitter(
                    FileManager(job.influencer_name),
                    job.sse_queue, job.decision_event, job.decision_store,
                )
                emitter_fb.emit("job_failed", {"job_id": job.job_id, "error": str(e)})
            except Exception:
                pass

    @staticmethod
    def _init_context(subject: dict) -> dict:
        ctx = {"대상자": subject}
        for key in get_context_keys():
            ctx[key] = None
        ctx["검증_결과"] = None
        ctx["보고_조건"] = None
        return ctx
