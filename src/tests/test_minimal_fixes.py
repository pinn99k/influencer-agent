import shutil
import types

import requests as _rq

import core.llm_client as llm
import agents.ceo as ceo_mod
from agents.ceo import CEO
from core.file_manager import FileManager
from core.config import OUTPUTS_DIR


class _Resp:
    status_code = 200
    def raise_for_status(self):
        pass
    def json(self):
        return {"choices": [{"message": {"content": "ok", "tool_calls": []}}]}


def test_call_llm_tools_retries_on_connection_error(monkeypatch):
    """Fix1: 연결 끊김은 크래시 대신 재시도한다."""
    calls = {"n": 0}

    def fake_post(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _rq.exceptions.ConnectionError("remote disconnected")
        return _Resp()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(llm.requests, "post", fake_post)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    out = llm.call_llm_tools("openai", "gpt-4o", [{"role": "user", "content": "hi"}], [])
    assert out["content"] == "ok"
    assert calls["n"] == 2  # 1회 실패 후 재시도 성공


def test_final_report_payload_includes_performance(monkeypatch):
    """Fix3: 최종리포트 합성 페이로드에 성과_기록이 들어간다."""
    captured = {}

    def fake_call_llm(provider, model, system, user, **kw):
        captured["user"] = user
        return (
            "# 김테스트 인플루언서 전략 보고서\n"
            "## 한 줄 결론\nx\n## 핵심 결정 3가지\n1.a\n## 강점과 기회\nx\n"
            "## 4주 실행 로드맵\n- Week 1: a\n## 지금 당장 할 3가지\n1.a\n"
            "## 성공 지표\n- 팔로워: 330\n## 매주 반복 루틴\n1.a\n"
            "## 성과 기록\nx\n## 2주 후 셀프 점검\nx\n"
        )

    monkeypatch.setattr(ceo_mod, "call_llm", fake_call_llm)
    name = "테스트_finalreport_fix"
    fm = FileManager(name)
    try:
        ceo = CEO(fm)
        ctx = {"대상자": {"이름": "김테스트"}, "성과_기록": "팔로워 330명 달성, 예약문의 4건"}
        ceo._synthesize_final_report(ctx)
        assert "팔로워 330명 달성" in captured["user"]
    finally:
        p = OUTPUTS_DIR / name
        if p.exists():
            shutil.rmtree(p)
