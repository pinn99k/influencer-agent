"""API route tests for Spiral 3 Web UI."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import queue
import threading

import pytest

# Ensure src/ is importable
_src = str(Path(__file__).resolve().parent.parent)
if _src not in sys.path:
    sys.path.insert(0, _src)

from fastapi.testclient import TestClient

from api.session_manager import SessionManager, JobContext
from api.main import app, session_mgr


client = TestClient(app)

VALID_SUBJECT = {
    "이름": "TestCreator",
    "직업": "developer",
    "특기": "coding",
    "성격": "introvert",
    "타겟연령대": "20s",
    "SNS경험": "none",
    "목표": "gain 1000 subscribers in 6 months",
}


# -- /api/start --

class TestStartEndpoint:
    def test_start_returns_job_id(self):
        with patch.object(session_mgr, "start_job", return_value="abc123"):
            resp = client.post("/api/start", json={"subject": VALID_SUBJECT})
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "abc123"
        assert data["status"] == "started"

    def test_start_rejects_missing_name(self):
        subject = {**VALID_SUBJECT, "이름": ""}
        resp = client.post("/api/start", json={"subject": subject})
        assert resp.status_code == 422

    def test_start_rejects_missing_goal(self):
        subject = {**VALID_SUBJECT, "목표": ""}
        resp = client.post("/api/start", json={"subject": subject})
        assert resp.status_code == 422

    def test_start_rejects_missing_subject(self):
        resp = client.post("/api/start", json={})
        assert resp.status_code == 422

    def test_start_returns_429_on_max_jobs(self):
        with patch.object(session_mgr, "start_job", side_effect=RuntimeError("Max")):
            resp = client.post("/api/start", json={"subject": VALID_SUBJECT})
        assert resp.status_code == 429


# -- /api/status --

class TestStatusEndpoint:
    def test_get_all_status(self):
        mock_jobs = [{"job_id": "a1", "influencer_name": "Test", "status": "running", "error": None}]
        with patch.object(session_mgr, "get_all_jobs", return_value=mock_jobs):
            resp = client.get("/api/status")
        assert resp.status_code == 200
        assert resp.json()["jobs"] == mock_jobs

    def test_get_job_status(self):
        mock_job = JobContext(
            job_id="a1", influencer_name="Test", subject=VALID_SUBJECT, status="running"
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job):
            resp = client.get("/api/status/a1")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_get_job_status_404(self):
        with patch.object(session_mgr, "get_job", return_value=None):
            resp = client.get("/api/status/nonexistent")
        assert resp.status_code == 404


# -- /api/decision --

class TestDecisionEndpoint:
    def test_submit_decision(self):
        with patch.object(session_mgr, "submit_decision"):
            resp = client.post("/api/decision/a1", json={"choice": "A", "reason": "better"})
        assert resp.status_code == 200
        assert resp.json()["choice"] == "A"

    def test_decision_404(self):
        with patch.object(session_mgr, "submit_decision", side_effect=KeyError("nope")):
            resp = client.post("/api/decision/bad", json={"choice": "A"})
        assert resp.status_code == 404

    def test_decision_409_wrong_state(self):
        with patch.object(session_mgr, "submit_decision", side_effect=ValueError("not waiting")):
            resp = client.post("/api/decision/a1", json={"choice": "A"})
        assert resp.status_code == 409


# -- /api/job (cancel) --

class TestCancelEndpoint:
    def test_cancel_job(self):
        with patch.object(session_mgr, "cancel_job"):
            resp = client.delete("/api/job/a1")
        assert resp.status_code == 200

    def test_cancel_404(self):
        with patch.object(session_mgr, "cancel_job", side_effect=KeyError("nope")):
            resp = client.delete("/api/job/bad")
        assert resp.status_code == 404


# -- /api/reports --

class TestReportsEndpoint:
    def test_list_reports(self, tmp_path):
        deliverables = tmp_path / "TestCreator" / "산출물"
        deliverables.mkdir(parents=True)
        (deliverables / "01_report.md").write_text("content", encoding="utf-8")
        (deliverables / "02_report.md").write_text("content", encoding="utf-8")

        with patch("api.routes.reports.OUTPUTS_DIR", tmp_path):
            resp = client.get("/api/reports/TestCreator")
        assert resp.status_code == 200
        assert len(resp.json()["reports"]) == 2

    def test_list_reports_404(self, tmp_path):
        with patch("api.routes.reports.OUTPUTS_DIR", tmp_path):
            resp = client.get("/api/reports/NoSuchPerson")
        assert resp.status_code == 404

    def test_get_report_content(self, tmp_path):
        deliverables = tmp_path / "TestCreator" / "산출물"
        deliverables.mkdir(parents=True)
        (deliverables / "01_report.md").write_text("# Hello", encoding="utf-8")

        with patch("api.routes.reports.OUTPUTS_DIR", tmp_path):
            resp = client.get("/api/reports/TestCreator/01_report.md")
        assert resp.status_code == 200
        assert resp.json()["content"] == "# Hello"

    def test_path_traversal_rejected(self):
        resp = client.get("/api/reports/<script>alert(1)</script>")
        assert resp.status_code == 400

    def test_invalid_filename_rejected(self):
        resp = client.get("/api/reports/TestCreator/;rm -rf.txt")
        assert resp.status_code == 400


# -- /api/stream --

class TestStreamEndpoint:
    def test_stream_404_for_unknown_job(self):
        with patch.object(session_mgr, "get_job", return_value=None):
            resp = client.get("/api/stream/nonexistent")
        assert resp.status_code == 404

    def test_stream_returns_sse_content_type(self):
        mock_queue = queue.Queue()
        mock_queue.put({"type": "job_completed", "timestamp": "2026-01-01"})
        mock_job = JobContext(
            job_id="a1", influencer_name="Test",
            subject=VALID_SUBJECT, sse_queue=mock_queue, status="running",
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job):
            resp = client.get("/api/stream/a1")
        assert "text/event-stream" in resp.headers.get("content-type", "")

# -- Enhanced status endpoint tests --

class TestEnhancedStatusEndpoint:
    """Tests for enhanced GET /api/status/{job_id} response."""

    def test_status_includes_subject(self):
        mock_job = JobContext(
            job_id="a1", influencer_name="Test",
            subject=VALID_SUBJECT, status="running"
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job):
            resp = client.get("/api/status/a1")
        data = resp.json()
        assert data["subject"] == VALID_SUBJECT
        assert data["subject"]["이름"] == "TestCreator"

    def test_status_includes_empty_reports_when_no_dir(self, tmp_path):
        mock_job = JobContext(
            job_id="a1", influencer_name="NoPerson",
            subject=VALID_SUBJECT, status="running"
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job), \
             patch("api.routes.ceo.OUTPUTS_DIR", tmp_path):
            resp = client.get("/api/status/a1")
        assert resp.json()["reports"] == []

    def test_status_lists_md_reports(self, tmp_path):
        deliverables = tmp_path / "Reporter" / "산출물"
        deliverables.mkdir(parents=True)
        (deliverables / "01_report.md").write_text("a", encoding="utf-8")
        (deliverables / "02_report.md").write_text("b", encoding="utf-8")
        (deliverables / "not_md.txt").write_text("c", encoding="utf-8")

        mock_job = JobContext(
            job_id="a1", influencer_name="Reporter",
            subject=VALID_SUBJECT, status="completed"
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job), \
             patch("api.routes.ceo.OUTPUTS_DIR", tmp_path):
            resp = client.get("/api/status/a1")
        reports = resp.json()["reports"]
        assert len(reports) == 2
        assert "01_report.md" in reports
        assert "not_md.txt" not in reports

    def test_status_includes_recent_events_from_emitter(self):
        mock_emitter = MagicMock()
        mock_emitter.get_recent_events.return_value = [
            {"type": "agent_start", "timestamp": "2026-01-01T00:00:00"},
            {"type": "agent_done", "timestamp": "2026-01-01T00:01:00"},
        ]
        mock_job = JobContext(
            job_id="a1", influencer_name="Test",
            subject=VALID_SUBJECT, status="running"
        )
        mock_job.emitter = mock_emitter
        with patch.object(session_mgr, "get_job", return_value=mock_job):
            resp = client.get("/api/status/a1")
        events = resp.json()["recent_events"]
        assert len(events) == 2
        assert events[0]["type"] == "agent_start"

    def test_status_returns_empty_events_when_no_emitter(self):
        mock_job = JobContext(
            job_id="a1", influencer_name="Test",
            subject=VALID_SUBJECT, status="pending"
        )
        # emitter is None by default
        with patch.object(session_mgr, "get_job", return_value=mock_job):
            resp = client.get("/api/status/a1")
        assert resp.json()["recent_events"] == []

    def test_status_includes_all_fields(self):
        mock_job = JobContext(
            job_id="xyz789", influencer_name="FullTest",
            subject=VALID_SUBJECT, status="failed", error="timeout"
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job):
            resp = client.get("/api/status/xyz789")
        data = resp.json()
        assert data["job_id"] == "xyz789"
        assert data["influencer_name"] == "FullTest"
        assert data["status"] == "failed"
        assert data["error"] == "timeout"
        assert "subject" in data
        assert "reports" in data
        assert "recent_events" in data


# -- EventEmitter ring buffer tests --

class TestEventEmitterRingBuffer:
    """Tests for EventEmitter deque-based history."""

    def _make_emitter(self):
        fm = MagicMock()
        q = queue.Queue()
        evt = threading.Event()
        store = {}
        from api.event_emitter import EventEmitter
        return EventEmitter(fm, q, evt, store)

    def test_get_recent_events_empty(self):
        emitter = self._make_emitter()
        assert emitter.get_recent_events() == []

    def test_get_recent_events_returns_emitted(self):
        emitter = self._make_emitter()
        emitter.emit("test_event", {"key": "value"})
        events = emitter.get_recent_events()
        assert len(events) == 1
        assert events[0]["type"] == "test_event"
        assert events[0]["key"] == "value"
        assert "timestamp" in events[0]

    def test_get_recent_events_limit(self):
        emitter = self._make_emitter()
        for i in range(10):
            emitter.emit("evt", {"n": i})
        assert len(emitter.get_recent_events(5)) == 5
        assert len(emitter.get_recent_events(20)) == 10

    def test_ring_buffer_maxlen(self):
        emitter = self._make_emitter()
        for i in range(60):
            emitter.emit("evt", {"n": i})
        events = emitter.get_recent_events(100)
        assert len(events) == 50  # maxlen=50
        assert events[0]["n"] == 10  # oldest kept = 60-50
        assert events[-1]["n"] == 59

    def test_emit_persists_to_file_manager(self):
        emitter = self._make_emitter()
        emitter.emit("hello", {"msg": "world"})
        emitter._fm.append_log.assert_called_once()
        logged = emitter._fm.append_log.call_args[0][0]
        assert logged["type"] == "hello"
        assert logged["msg"] == "world"

    def test_status_includes_subject(self):
        mock_job = JobContext(
            job_id="a1", influencer_name="Test",
            subject=VALID_SUBJECT, status="running"
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job):
            resp = client.get("/api/status/a1")
        data = resp.json()
        assert data["subject"] == VALID_SUBJECT
        assert data["subject"]["이름"] == "TestCreator"

    def test_status_includes_empty_reports_when_no_dir(self, tmp_path):
        mock_job = JobContext(
            job_id="a1", influencer_name="NoPerson",
            subject=VALID_SUBJECT, status="running"
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job), \
             patch("api.routes.ceo.OUTPUTS_DIR", tmp_path):
            resp = client.get("/api/status/a1")
        assert resp.json()["reports"] == []

    def test_status_lists_md_reports(self, tmp_path):
        deliverables = tmp_path / "Reporter" / "산출물"
        deliverables.mkdir(parents=True)
        (deliverables / "01_report.md").write_text("a", encoding="utf-8")
        (deliverables / "02_report.md").write_text("b", encoding="utf-8")
        (deliverables / "not_md.txt").write_text("c", encoding="utf-8")

        mock_job = JobContext(
            job_id="a1", influencer_name="Reporter",
            subject=VALID_SUBJECT, status="completed"
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job), \
             patch("api.routes.ceo.OUTPUTS_DIR", tmp_path):
            resp = client.get("/api/status/a1")
        reports = resp.json()["reports"]
        assert len(reports) == 2
        assert "01_report.md" in reports
        assert "not_md.txt" not in reports

    def test_status_includes_recent_events_from_emitter(self):
        mock_emitter = MagicMock()
        mock_emitter.get_recent_events.return_value = [
            {"type": "agent_start", "timestamp": "2026-01-01T00:00:00"},
            {"type": "agent_done", "timestamp": "2026-01-01T00:01:00"},
        ]
        mock_job = JobContext(
            job_id="a1", influencer_name="Test",
            subject=VALID_SUBJECT, status="running"
        )
        mock_job.emitter = mock_emitter
        with patch.object(session_mgr, "get_job", return_value=mock_job):
            resp = client.get("/api/status/a1")
        events = resp.json()["recent_events"]
        assert len(events) == 2
        assert events[0]["type"] == "agent_start"

    def test_status_returns_empty_events_when_no_emitter(self):
        mock_job = JobContext(
            job_id="a1", influencer_name="Test",
            subject=VALID_SUBJECT, status="pending"
        )
        # emitter is None by default
        with patch.object(session_mgr, "get_job", return_value=mock_job):
            resp = client.get("/api/status/a1")
        assert resp.json()["recent_events"] == []

    def test_status_includes_all_fields(self):
        mock_job = JobContext(
            job_id="xyz789", influencer_name="FullTest",
            subject=VALID_SUBJECT, status="failed", error="timeout"
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job):
            resp = client.get("/api/status/xyz789")
        data = resp.json()
        assert data["job_id"] == "xyz789"
        assert data["influencer_name"] == "FullTest"
        assert data["status"] == "failed"
        assert data["error"] == "timeout"
        assert "subject" in data
        assert "reports" in data
        assert "recent_events" in data


# -- EventEmitter ring buffer tests --

class TestEventEmitterRingBuffer:
    """Tests for EventEmitter deque-based history."""

    def _make_emitter(self):
        fm = MagicMock()
        q = queue.Queue()
        evt = threading.Event()
        store = {}
        from api.event_emitter import EventEmitter
        return EventEmitter(fm, q, evt, store)

    def test_get_recent_events_empty(self):
        emitter = self._make_emitter()
        assert emitter.get_recent_events() == []

    def test_get_recent_events_returns_emitted(self):
        emitter = self._make_emitter()
        emitter.emit("test_event", {"key": "value"})
        events = emitter.get_recent_events()
        assert len(events) == 1
        assert events[0]["type"] == "test_event"
        assert events[0]["key"] == "value"
        assert "timestamp" in events[0]

    def test_get_recent_events_limit(self):
        emitter = self._make_emitter()
        for i in range(10):
            emitter.emit("evt", {"n": i})
        assert len(emitter.get_recent_events(5)) == 5
        assert len(emitter.get_recent_events(20)) == 10

    def test_ring_buffer_maxlen(self):
        emitter = self._make_emitter()
        for i in range(60):
            emitter.emit("evt", {"n": i})
        events = emitter.get_recent_events(100)
        assert len(events) == 50  # maxlen=50
        assert events[0]["n"] == 10  # oldest kept = 60-50
        assert events[-1]["n"] == 59

    def test_emit_persists_to_file_manager(self):
        emitter = self._make_emitter()
        emitter.emit("hello", {"msg": "world"})
        emitter._fm.append_log.assert_called_once()
        logged = emitter._fm.append_log.call_args[0][0]
        assert logged["type"] == "hello"
        assert logged["msg"] == "world"


# -- /api/agent-output --

class TestAgentOutputEndpoint:
    """Tests for GET /api/agent-output/{job_id}/{agent_key}"""

    def test_get_agent_output_success(self, tmp_path):
        # Create mock raw_output file
        agent_dir = tmp_path / "TestCreator" / ".system" / "agents" / "대상분석"
        agent_dir.mkdir(parents=True)
        (agent_dir / "raw_output.md").write_text("# Analysis Result\nContent here", encoding="utf-8")

        mock_job = JobContext(
            job_id="a1", influencer_name="TestCreator",
            subject=VALID_SUBJECT, status="completed"
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job), \
             patch("api.routes.ceo.OUTPUTS_DIR", tmp_path):
            resp = client.get("/api/agent-output/a1/대상분석")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent"] == "대상분석"
        assert "Analysis Result" in data["content"]

    def test_get_agent_output_job_not_found(self):
        with patch.object(session_mgr, "get_job", return_value=None):
            resp = client.get("/api/agent-output/bad/대상분석")
        assert resp.status_code == 404

    def test_get_agent_output_invalid_agent(self):
        mock_job = JobContext(
            job_id="a1", influencer_name="TestCreator",
            subject=VALID_SUBJECT, status="completed"
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job):
            resp = client.get("/api/agent-output/a1/invalid_agent")
        assert resp.status_code == 400

    def test_get_agent_output_file_not_found(self, tmp_path):
        mock_job = JobContext(
            job_id="a1", influencer_name="TestCreator",
            subject=VALID_SUBJECT, status="running"
        )
        with patch.object(session_mgr, "get_job", return_value=mock_job), \
             patch("api.routes.ceo.OUTPUTS_DIR", tmp_path):
            resp = client.get("/api/agent-output/a1/대상분석")
        assert resp.status_code == 404
