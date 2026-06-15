"""U1 tests — DirectionProfile model + FileManager persistence (TDD).

DirectionProfile is the structured user-chosen direction (content focus, target
goal, strategy focus areas, free notes). It feeds the strategy through the same
ceo_summary injection path as feedback.
"""
import shutil

import pytest

from core.direction import DirectionProfile
from core.file_manager import FileManager
from core.config import OUTPUTS_DIR


# ---- DirectionProfile model (pure, no disk) ------------------------------

def test_is_empty_true_when_blank():
    assert DirectionProfile().is_empty()


def test_is_empty_false_when_any_field_set():
    assert not DirectionProfile(content_focus="연습영상 위주").is_empty()
    assert not DirectionProfile(strategy_focus=["해시태그"]).is_empty()


def test_markdown_roundtrip_preserves_fields():
    d = DirectionProfile(
        content_focus="연습영상 위주",
        target_goal="팔로워 100만",
        strategy_focus=["프로필 꾸미기", "해시태그", "영상 편집"],
        notes="자유 메모 내용",
    )
    parsed = DirectionProfile.from_markdown(d.to_markdown(name="테스트"))
    assert parsed.content_focus == d.content_focus
    assert parsed.target_goal == d.target_goal
    assert parsed.strategy_focus == d.strategy_focus
    assert parsed.notes == d.notes


def test_to_markdown_includes_name():
    md = DirectionProfile(content_focus="x").to_markdown(name="김미용")
    assert "김미용" in md


def test_from_markdown_handles_missing_sections():
    # Only one section present -> others default empty, no crash.
    d = DirectionProfile.from_markdown("# 방향\n\n## 핵심 목표\n팔로워 100만\n")
    assert d.target_goal == "팔로워 100만"
    assert d.content_focus == ""
    assert d.strategy_focus == []


def test_to_prompt_text_excludes_empty_fields():
    d = DirectionProfile(content_focus="연습영상", strategy_focus=[])
    txt = d.to_prompt_text()
    assert "연습영상" in txt
    assert "중점 전략" not in txt   # empty list omitted


def test_to_prompt_text_empty_when_all_blank():
    assert DirectionProfile().to_prompt_text() == ""


# ---- FileManager persistence ---------------------------------------------

INFLUENCER = "테스트_direction"
BASE = OUTPUTS_DIR / INFLUENCER


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if BASE.exists():
        shutil.rmtree(BASE)


def test_save_then_load_direction():
    fm = FileManager(INFLUENCER)
    fm.save_direction("# 방향\n## 콘텐츠 방향\n연습영상 위주\n")
    loaded = fm.load_direction()
    assert loaded is not None
    assert "연습영상 위주" in loaded


def test_load_direction_none_when_absent():
    fm = FileManager(INFLUENCER)
    assert fm.load_direction() is None


# ---- U2: direction injection into strategy (reuses feedback path) ---------

from unittest.mock import MagicMock, patch  # noqa: E402

from agents.subject_analyst import SubjectAnalystAgent  # noqa: E402
from tests.conftest import SAMPLE_SUBJECT  # noqa: E402

_DIR_MARKER = "PRACTICE_VIDEO_FOCUS_2026"


def _ceo(fm=None):
    from agents.ceo import CEO
    return CEO(fm or MagicMock(), dry_run=False)


def test_ceo_summary_includes_direction_verbatim():
    ctx = {"대상자": {"이름": "T"}, "방향": "방향 지시\n- 콘텐츠 방향: " + _DIR_MARKER}
    with patch("agents.ceo.call_llm", return_value="전략 요약"):
        _ceo()._build_ceo_summary(ctx)
    assert _DIR_MARKER in ctx["ceo_summary"]


def test_direction_reaches_agent_prompt():
    # direction -> ceo_summary -> agent prompt (same path feedback uses)
    ctx = {"대상자": {"이름": "T"}, "방향": "- 콘텐츠 방향: " + _DIR_MARKER}
    with patch("agents.ceo.call_llm", return_value="전략 요약"):
        _ceo()._build_ceo_summary(ctx)
    prompt = SubjectAnalystAgent().build_prompt(ctx)
    assert _DIR_MARKER in prompt


def test_load_direction_sets_context_when_present():
    fm = MagicMock()
    fm.load_direction.return_value = "방향 내용 " + _DIR_MARKER
    ctx = {}
    _ceo(fm)._load_direction(ctx)
    assert _DIR_MARKER in ctx.get("방향", "")


def test_load_direction_noop_when_absent():
    fm = MagicMock()
    fm.load_direction.return_value = None
    ctx = {}
    _ceo(fm)._load_direction(ctx)
    assert "방향" not in ctx
