import collections
import queue
import threading
import datetime
from typing import Optional

from core.file_manager import FileManager


class EventEmitter:
    """Bridges CEO events to SSE consumers and JSONL persistence.

    Three output channels:
      1. queue.Queue -> SSE endpoint reads this for real-time streaming
      2. FileManager.append_log() -> JSONL file persistence
      3. deque ring buffer -> page-reload recovery via GET /status/{job_id}
    """

    def __init__(
        self,
        file_manager: FileManager,
        sse_queue: queue.Queue,
        decision_event: threading.Event,
        decision_store: dict,
        job_context=None,
    ):
        self._fm = file_manager
        self._queue = sse_queue
        self._decision_event = decision_event
        self._decision_store = decision_store
        self._job_context = job_context
        self._history: collections.deque = collections.deque(maxlen=50)

    def emit(self, event_type: str, data: Optional[dict] = None) -> None:
        event = {
            "type": event_type,
            "timestamp": datetime.datetime.now().isoformat(),
            **(data or {}),
        }
        self._fm.append_log(event)
        self._history.append(event)
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            pass

    def get_recent_events(self, limit: int = 20) -> list[dict]:
        """Return last N events from ring buffer for page-reload recovery."""
        return list(self._history)[-limit:]

    def wait_for_decision(self, timeout: int = 3600) -> Optional[dict]:
        """Block until chairman submits decision via POST /decision.
        Returns decision dict or None on timeout."""
        if self._job_context is not None:
            self._job_context.status = "waiting_decision"
        self._decision_event.clear()
        signaled = self._decision_event.wait(timeout=timeout)
        if self._job_context is not None:
            self._job_context.status = "running"
        if signaled:
            return self._decision_store.get("decision")
        return None
