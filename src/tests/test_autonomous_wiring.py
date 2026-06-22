"""2장 자율루프 제품 연결 -- CLI(--autonomous) + 웹(SessionManager mode) 배선 검증.

실 LLM 없이 CEO를 가짜로 대체해 어떤 메서드가 호출되는지만 확인한다.
"""
import sys

from api import session_manager as sm
from api.session_manager import SessionManager, JobContext


# ──────────────────────────────────────────────
# 웹: SessionManager mode 라우팅
# ──────────────────────────────────────────────

class _FakeCEO:
    last = {}

    def __init__(self, fm, dry_run=False, event_emitter=None):
        pass

    def run(self, context):
        _FakeCEO.last["method"] = "run"

    def run_autonomous(self, context):
        _FakeCEO.last["method"] = "run_autonomous"


class _FakeFM:
    def __init__(self, name):
        self.name = name


class _FakeEmitter:
    def __init__(self, *a, **k):
        pass

    def emit(self, *a, **k):
        pass

    def get_recent_events(self, n):
        return []


def _patch_run_ceo_deps(monkeypatch):
    monkeypatch.setattr(sm, "CEO", _FakeCEO)
    monkeypatch.setattr(sm, "FileManager", _FakeFM)
    monkeypatch.setattr(sm, "EventEmitter", _FakeEmitter)


def _subject():
    return {"이름": "테스트", "목표": "여섯달 안에 팔로워 늘리기"}


def test_run_ceo_linear_calls_run(monkeypatch):
    _patch_run_ceo_deps(monkeypatch)
    _FakeCEO.last.clear()
    mgr = SessionManager()
    job = JobContext(job_id="t1", influencer_name="테스트", subject=_subject(), mode="linear")
    mgr._run_ceo(job)
    assert _FakeCEO.last["method"] == "run"
    assert job.status == "completed"


def test_run_ceo_autonomous_calls_run_autonomous(monkeypatch):
    _patch_run_ceo_deps(monkeypatch)
    _FakeCEO.last.clear()
    mgr = SessionManager()
    job = JobContext(job_id="t2", influencer_name="테스트", subject=_subject(), mode="autonomous")
    mgr._run_ceo(job)
    assert _FakeCEO.last["method"] == "run_autonomous"
    assert job.status == "completed"


def test_start_job_stores_autonomous_mode(monkeypatch):
    monkeypatch.setattr(SessionManager, "_run_ceo", lambda self, job: None)
    mgr = SessionManager()
    jid = mgr.start_job(_subject(), mode="autonomous")
    job = mgr.get_job(jid)
    if job.thread:
        job.thread.join(timeout=2)
    assert job.mode == "autonomous"


def test_start_job_defaults_to_linear(monkeypatch):
    monkeypatch.setattr(SessionManager, "_run_ceo", lambda self, job: None)
    mgr = SessionManager()
    jid = mgr.start_job(_subject())
    job = mgr.get_job(jid)
    if job.thread:
        job.thread.join(timeout=2)
    assert job.mode == "linear"


# ──────────────────────────────────────────────
# CLI: --autonomous 플래그
# ──────────────────────────────────────────────

class _CliFakeCEO:
    calls = {}

    def __init__(self, fm, dry_run=False, event_emitter=None):
        pass

    def run(self, context):
        _CliFakeCEO.calls["method"] = "run"

    def run_autonomous(self, context):
        _CliFakeCEO.calls["method"] = "run_autonomous"


class _CliFakeFM:
    def __init__(self, name):
        pass

    def init_performance_record(self):
        return "perf.md"

    def init_feedback_template(self):
        return "feedback.md"


def _patch_cli(monkeypatch):
    import main as cli
    monkeypatch.setattr(cli, "CEO", _CliFakeCEO)
    monkeypatch.setattr(cli, "FileManager", _CliFakeFM)
    # legacy 폼 입력값 (목표는 10자 이상이라 재입력 분기 회피)
    answers = iter([
        "테스트", "미용사", "헤어컬러", "내향적",
        "20대", "인스타 200명", "여섯달 안에 팔로워 오천명 달성",
    ])
    monkeypatch.setattr("builtins.input", lambda *a, **k: next(answers))
    return cli


def test_cli_autonomous_flag_runs_autonomous(monkeypatch):
    cli = _patch_cli(monkeypatch)
    _CliFakeCEO.calls.clear()
    monkeypatch.setattr(sys, "argv", ["main.py", "--legacy", "--autonomous"])
    cli.main()
    assert _CliFakeCEO.calls["method"] == "run_autonomous"


def test_cli_default_runs_linear(monkeypatch):
    cli = _patch_cli(monkeypatch)
    _CliFakeCEO.calls.clear()
    monkeypatch.setattr(sys, "argv", ["main.py", "--legacy"])
    cli.main()
    assert _CliFakeCEO.calls["method"] == "run"
