"""Quick smoke test for reanalyze API endpoints."""
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from api.main import app
from core.config import OUTPUTS_DIR

client = TestClient(app)

# The feedback/performance PUTs below write under outputs/김민수 — clean it up so
# test runs never pollute the real workspace (.claude/lessons hygiene).
_KIM = OUTPUTS_DIR / "김민수"


@pytest.fixture(autouse=True)
def _cleanup_outputs():
    existed_before = _KIM.exists()
    yield
    if _KIM.exists() and not existed_before:
        shutil.rmtree(_KIM)


def test_subjects():
    r = client.get("/api/subjects")
    assert r.status_code == 200
    data = r.json()
    assert "subjects" in data
    assert isinstance(data["subjects"], list)
    print(f"  subjects: {len(data['subjects'])} found")
    for s in data["subjects"][:5]:
        print(f"    {s['name']}: out={s['has_outputs']} fb={s['has_feedback']} perf={s['has_performance']}")


def test_feedback_get():
    r = client.get("/api/feedback/%EA%B9%80%EB%AF%BC%EC%88%98")  # 김민수
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    print(f"  feedback content exists: {data['content'] is not None}")


def test_feedback_put():
    r = client.put(
        "/api/feedback/%EA%B9%80%EB%AF%BC%EC%88%98",
        json={"content": "test feedback content"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "saved"
    print("  feedback saved OK")


def test_performance_get():
    r = client.get("/api/performance/%EA%B9%80%EB%AF%BC%EC%88%98")
    assert r.status_code == 200
    data = r.json()
    assert "content" in data
    print(f"  performance content exists: {data['content'] is not None}")


def test_performance_put():
    r = client.put(
        "/api/performance/%EA%B9%80%EB%AF%BC%EC%88%98",
        json={"content": "test performance content"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "saved"
    print("  performance saved OK")


def test_reanalyze_no_outputs():
    r = client.post("/api/reanalyze", json={"name": "nonexistent_person_xyz"})
    assert r.status_code == 404
    print("  reanalyze 404 for nonexistent: OK")


def test_reanalyze_invalid_name():
    r = client.post("/api/reanalyze", json={"name": "../../../etc"})
    assert r.status_code == 400
    print("  reanalyze 400 for invalid name: OK")


def test_static_mvc_layers():
    """Frontend split into MVC layers (app.js removed). Verify each symbol
    lives in its correct layer and old app.js is gone."""
    # old monolith is gone
    assert client.get("/app.js").status_code == 404

    # api layer: REST client methods
    api_js = client.get("/api.js")
    assert api_js.status_code == 200
    assert "listSubjects" in api_js.text
    assert "interviewStart" in api_js.text
    assert "openStream" in api_js.text

    # actions layer: controller logic (no fetch here besides via API.*)
    actions_js = client.get("/actions.js")
    assert actions_js.status_code == 200
    assert "startReanalyze" in actions_js.text
    assert "confirmInterview" in actions_js.text

    # model layer: pure state, must NOT contain action logic
    model_js = client.get("/model.js")
    assert model_js.status_code == 200
    assert "subscribe" in model_js.text
    assert "startReanalyze" not in model_js.text  # actions moved out

    # views layer: render functions
    views_js = client.get("/views.js")
    assert views_js.status_code == 200
    for sym in ("viewReanalyzeEntry", "viewInterview", "viewManagerPanel"):
        assert sym in views_js.text
    # views call Actions, never fetch directly
    assert "fetch(" not in views_js.text
    print("  MVC layers OK: api/actions/model/views split verified")


if __name__ == "__main__":
    tests = [
        test_subjects,
        test_feedback_get,
        test_feedback_put,
        test_performance_get,
        test_performance_put,
        test_reanalyze_no_outputs,
        test_reanalyze_invalid_name,
        test_static_mvc_layers,
    ]
    passed = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"PASS {name}")
            passed += 1
        except Exception as e:
            print(f"FAIL {name}: {e}")

    print(f"\n{passed}/{len(tests)} passed")
