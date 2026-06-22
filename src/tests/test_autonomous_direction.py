"""run_autonomous가 run()과 동일하게 성과·방향을 주입하는지 (F1 회귀 가드)."""
import shutil

import agents.ceo as ceo_mod
from agents.ceo import CEO
from core.file_manager import FileManager
from core.config import OUTPUTS_DIR


class _FakeLoop:
    def __init__(self, *a, **k):
        pass

    def run(self, msg):
        return {"iterations": 1, "finished": True, "ran": [],
                "stop_reason": "finish", "messages": []}


def test_run_autonomous_injects_direction_and_perf(monkeypatch):
    name = "_자율방향테스트_"
    base = OUTPUTS_DIR / name
    try:
        ceo = CEO(FileManager(name), dry_run=False)
        order = []
        monkeypatch.setattr(ceo.fm, "load_performance_record", lambda: "PERF")

        def _fake_dir(ctx):
            order.append("dir")
            ctx["방향"] = "DIR"

        monkeypatch.setattr(ceo, "_load_direction", _fake_dir)
        monkeypatch.setattr(ceo, "_build_ceo_summary", lambda ctx: order.append("summary"))
        monkeypatch.setattr(ceo, "_finalize", lambda ctx: None)
        monkeypatch.setattr(ceo_mod, "AgentLoop", _FakeLoop)

        ctx = {"대상자": {"이름": name, "목표": "여섯달 안에 팔로워 늘리기"}}
        ceo.run_autonomous(ctx)

        assert ctx.get("성과_기록") == "PERF"
        assert ctx.get("방향") == "DIR"
        # 방향/성과는 전략요약(_build_ceo_summary)보다 먼저 주입돼야 한다.
        assert order == ["dir", "summary"]
    finally:
        if base.exists():
            shutil.rmtree(base, ignore_errors=True)
