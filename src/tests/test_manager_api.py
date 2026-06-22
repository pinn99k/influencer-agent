import shutil

from fastapi.testclient import TestClient

from api.main import app
from core.file_manager import FileManager
from core.config import OUTPUTS_DIR


client = TestClient(app)

_NAME = "mgrtest_api"
_BASE = OUTPUTS_DIR / _NAME


def _cleanup():
    if _BASE.exists():
        shutil.rmtree(_BASE)


def test_load_manager_outputs_maps_kind_and_week():
    _cleanup()
    fm = FileManager(_NAME)
    fm.save_manager_output("weekly_card_week1.md", "# 이번 주 할 일")
    fm.save_manager_output("performance_request_week2.md", "# 성과 입력 요청")
    fm.save_manager_output("progress_report_2026-06-21.md", "# 진행 보고")
    try:
        notes = fm.load_manager_outputs()
        kinds = {n["kind"] for n in notes}
        assert kinds == {"weekly_card", "performance_request", "progress"}
        weekly = next(n for n in notes if n["kind"] == "weekly_card")
        assert weekly["week"] == 1
        perf = next(n for n in notes if n["kind"] == "performance_request")
        assert perf["week"] == 2
    finally:
        _cleanup()


def test_get_manager_notes_endpoint():
    _cleanup()
    fm = FileManager(_NAME)
    fm.save_manager_output("weekly_card_week1.md", "# 이번 주 할 일\n- 촬영 3개")
    try:
        res = client.get("/api/manager/" + _NAME)
        assert res.status_code == 200
        data = res.json()
        assert data["influencer"] == _NAME
        assert len(data["notes"]) == 1
        assert data["notes"][0]["kind"] == "weekly_card"
        assert data["notes"][0]["week"] == 1
    finally:
        _cleanup()


def test_get_manager_notes_missing_returns_empty():
    res = client.get("/api/manager/nosuchsubject_xyz")
    assert res.status_code == 200
    assert res.json()["notes"] == []


def test_get_manager_notes_invalid_name_returns_400():
    res = client.get("/api/manager/bad!name")
    assert res.status_code == 400
