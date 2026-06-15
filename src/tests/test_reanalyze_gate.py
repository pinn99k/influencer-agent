"""U2 — 재분석 게이트 테스트.

핵심 회귀 방지:
  - 새 입력(성과/피드백/방향)이 전혀 없으면 재분석이 전체 재실행되지 않는다.
    * _decide_rerun -> [] (빈 리스트)
    * run_reanalyze -> 'reanalyze_skipped' emit
    * POST /api/reanalyze -> 400 (잡 시작 전 차단)
  - 방향(방향.md)도 유효한 입력 신호로 카운트된다.
  - all-미정 방향은 입력으로 치지 않는다 (direction_has_content).
"""
import shutil
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import api.main as main_mod
import api.routes.reanalyze as rean_mod
from agents.ceo import CEO
from core.config import OUTPUTS_DIR
from core.direction import direction_has_content, DirectionProfile

NAME = "테스트_재분석게이트"
BASE = OUTPUTS_DIR / NAME


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if BASE.exists():
        shutil.rmtree(BASE)


def _mock_fm(**over):
    fm = MagicMock()
    fm.name = NAME
    fm.load_existing_outputs.return_value = {}
    fm.load_performance_record.return_value = None
    fm.load_feedback.return_value = None
    fm.load_direction.return_value = None
    for k, v in over.items():
        getattr(fm, k).return_value = v
    return fm


# ── direction_has_content (단위) ──────────────────────────────

def test_direction_has_content_blank_and_placeholder():
    assert direction_has_content("") is False
    assert direction_has_content("# 방향\n\n## 콘텐츠 방향\n미정\n\n## 핵심 목표\n미정") is False


def test_direction_has_content_real():
    md = DirectionProfile(content_focus="연습영상 위주").to_markdown("핑구")
    assert direction_has_content(md) is True


# ── _decide_rerun ─────────────────────────────────────────────

def test_decide_rerun_no_input_returns_empty():
    ceo = CEO(_mock_fm(), dry_run=True)
    out = ceo._decide_rerun({"대상자": {"이름": "T"}})
    assert out == []
    assert "입력 없음" in ceo._last_rerun_reason


def test_decide_rerun_direction_counts_as_input():
    ceo = CEO(_mock_fm(), dry_run=True)
    with patch("agents.ceo.call_llm",
               return_value='{"rerun_agents": ["컨셉기획"], "reason": "방향 반영"}'):
        out = ceo._decide_rerun({"대상자": {"이름": "T"}, "방향": "연습영상 위주"})
    assert out == ["컨셉기획"]


# ── _load_direction: all-미정은 주입 안 함 ────────────────────

def test_load_direction_skips_blank():
    blank = "# 방향\n\n## 콘텐츠 방향\n미정\n\n## 핵심 목표\n미정\n\n## 중점 전략\n- 미정"
    ceo = CEO(_mock_fm(load_direction=blank), dry_run=True)
    ctx = {"대상자": {"이름": "T"}}
    ceo._load_direction(ctx)
    assert "방향" not in ctx


def test_load_direction_injects_real():
    real = DirectionProfile(content_focus="연습영상 위주").to_markdown("T")
    ceo = CEO(_mock_fm(load_direction=real), dry_run=True)
    ctx = {"대상자": {"이름": "T"}}
    ceo._load_direction(ctx)
    assert ctx.get("방향")


# ── run_reanalyze: 무입력이면 skip emit ───────────────────────

def test_run_reanalyze_emits_skipped_when_no_input():
    emitter = MagicMock()
    ceo = CEO(_mock_fm(), dry_run=True, event_emitter=emitter)
    ceo.run_reanalyze({"대상자": {"이름": NAME}})
    types = [c.args[0] for c in emitter.emit.call_args_list if c.args]
    assert "reanalyze_skipped" in types


# ── API: POST /api/reanalyze 게이트 ───────────────────────────

@pytest.fixture
def client():
    return TestClient(main_mod.app)


def _make_subject_with_outputs():
    deliv = BASE / "산출물"
    deliv.mkdir(parents=True, exist_ok=True)
    (deliv / "01_대상분석.md").write_text("# 대상분석\n내용", encoding="utf-8")


def test_reanalyze_blocked_without_input(client):
    _make_subject_with_outputs()
    r = client.post("/api/reanalyze", json={"name": NAME})
    assert r.status_code == 400


def test_reanalyze_allowed_with_feedback(client):
    _make_subject_with_outputs()
    fake_mgr = MagicMock()
    fake_mgr.start_reanalyze_job.return_value = "job_test_123"
    with patch.object(rean_mod, "_session_mgr", fake_mgr):
        r = client.post("/api/reanalyze",
                        json={"name": NAME, "feedback": "컨셉 B로 바꿔줘"})
    assert r.status_code == 200
    assert r.json()["job_id"] == "job_test_123"
