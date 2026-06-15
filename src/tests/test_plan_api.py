from fastapi.testclient import TestClient

from api.main import app
from core import config


client = TestClient(app)


def test_get_plan_returns_structured_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path)
    import api.routes.plan as plan_route

    monkeypatch.setattr(plan_route, "OUTPUTS_DIR", tmp_path)
    base = tmp_path / "tester" / "\uc0b0\ucd9c\ubb3c"
    base.mkdir(parents=True)
    (base / "04_\ucee8\uc149\uae30\ud68d.md").write_text(
        "#### Week 1\n- reel one\n\n#### Week 2\n- post one\n",
        encoding="utf-8",
    )
    (base / "\ucd5c\uc885\ub9ac\ud3ec\ud2b8.md").write_text(
        "## \uc9c0\uae08 \ub2f9\uc7a5 \ud560 3\uac00\uc9c0\n"
        "1. first action\n"
        "\n## \uc131\uacf5 \uc9c0\ud45c (30\uc77c)\n"
        "- followers: 300\n",
        encoding="utf-8",
    )

    res = client.get("/api/plan/tester")

    assert res.status_code == 200
    data = res.json()
    assert data["influencer"] == "tester"
    assert data["weeks"][0]["items"] == ["reel one"]
    assert data["weeks"][1]["items"] == ["post one"]
    assert data["next_actions"] == ["first action"]
    assert data["kpi"] == ["followers: 300"]


def test_get_plan_missing_outputs_returns_404(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUTS_DIR", tmp_path)
    import api.routes.plan as plan_route

    monkeypatch.setattr(plan_route, "OUTPUTS_DIR", tmp_path)

    res = client.get("/api/plan/missing")

    assert res.status_code == 404


def test_get_plan_invalid_name_returns_400():
    res = client.get("/api/plan/bad!name")

    assert res.status_code == 400
