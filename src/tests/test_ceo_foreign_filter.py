"""Unit tests: _FOREIGN_CHAR_RE strips Japanese kana; CEO paths apply it."""
from unittest.mock import MagicMock, patch

from agents.base_agent import _FOREIGN_CHAR_RE


# ---- pure regex unit tests -----------------------------------------------

def test_hiragana_stripped():
    hiragana = "\u3053\u3093\u306b\u3061\u306f"
    assert _FOREIGN_CHAR_RE.sub("", hiragana) == ""


def test_katakana_stripped():
    katakana = "\u30b9\u30bf\u30a4\u30ea\u30b9\u30c8"
    assert _FOREIGN_CHAR_RE.sub("", katakana) == ""


def test_cjk_han_stripped():
    han = "\u5206\u6790"
    assert _FOREIGN_CHAR_RE.sub("", han) == ""


def test_korean_preserved():
    korean = "\ubbf8\uc6a9\uc0ac \ubd84\uc11d"
    assert _FOREIGN_CHAR_RE.sub("", korean) == korean


def test_mixed_strips_only_foreign():
    mixed = "\ubbf8\uc6a9 \u30b9\ud0c0\uc77c \ubaa9\ud45c"
    cleaned = _FOREIGN_CHAR_RE.sub("", mixed)
    assert "\u30b9" not in cleaned
    assert "\ubbf8\uc6a9" in cleaned
    assert "\ubaa9\ud45c" in cleaned


# ---- CEO integration tests ------------------------------------------------

def test_ceo_build_summary_strips_japanese():
    """CEO._build_ceo_summary applies the filter to LLM output."""
    llm_out = "\uc694\uc57d \u30c6\u30b9\u30c8 summary"
    with patch("agents.ceo.call_llm", return_value=llm_out):
        ceo = CEO_factory()
        ctx = {"\ub300\uc0c1\uc790": {"\uc774\ub984": "Test"}}
        ceo._build_ceo_summary(ctx)
    assert "\u30c6\u30b9\u30c8" not in ctx.get("ceo_summary", "")
    assert "\uc694\uc57d" in ctx.get("ceo_summary", "")


def test_ceo_interpret_goal_strips_japanese():
    """CEO._interpret_goal applies the filter before saving plan."""
    llm_out = "plan \u30c6\u30b9\u30c8 content"
    with patch("agents.ceo.call_llm", return_value=llm_out):
        fm = MagicMock()
        from agents.ceo import CEO
        ceo = CEO(fm, dry_run=False)
        ctx = {
            "\ub300\uc0c1\uc790": {
                "\uc774\ub984": "Test",
                "\ubaa9\ud45c": "goal",
            }
        }
        ceo._interpret_goal(ctx)
    saved = fm.save_plan.call_args[0][0]
    assert "\u30c6\u30b9\u30c8" not in saved
    assert "plan" in saved


def CEO_factory():
    from agents.ceo import CEO
    return CEO(MagicMock(), dry_run=False)
