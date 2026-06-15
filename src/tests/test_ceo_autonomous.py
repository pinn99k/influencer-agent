"""CEO.run_autonomous 와이어링 단위 테스트 (루프 mock)."""
import shutil

import pytest
from unittest.mock import MagicMock

from agents.ceo import CEO
from core.config import OUTPUTS_DIR

NAME = "테스트_자율"
BASE = OUTPUTS_DIR / NAME


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if BASE.exists():
        shutil.rmtree(BASE)


def test_run_autonomous_dry_run_no_llm():
    fm = MagicMock()
    fm.name = NAME
    ceo = CEO(fm, dry_run=True)
    out = ceo.run_autonomous({"대상자": {"이름": NAME, "목표": "g"}})
    assert out["ran"] == []
    assert out["finished"] is False


def test_run_autonomous_wires_loop(monkeypatch):
    import agents.ceo as ceomod
    fm = MagicMock()
    fm.name = NAME
    ceo = CEO(fm, dry_run=False)
    monkeypatch.setattr(ceo, "_build_ceo_summary", lambda ctx: ctx.__setitem__("ceo_summary", "s"))
    monkeypatch.setattr(ceo, "_finalize", lambda ctx: None)

    class FakeLoop:
        def __init__(self, *a, **k):
            pass

        def run(self, user_msg):
            return {"iterations": 2, "finished": True, "ran": ["대상분석"], "messages": []}

    monkeypatch.setattr(ceomod, "AgentLoop", FakeLoop)
    out = ceo.run_autonomous({"대상자": {"이름": NAME, "목표": "g"}})
    assert out["finished"] is True
    assert out["ran"] == ["대상분석"]
