"""Tests for PlanningDepartment layer and ConceptPlanner two-pass generation."""
import pytest
from unittest.mock import patch, MagicMock

from departments.planning import PlanningDepartment, DepartmentResult, _COMPRESS_SYSTEM, _BRIEFING_SYSTEM
from agents.concept_planner import ConceptPlannerAgent
from agents.base_agent import _FOREIGN_CHAR_RE


# ── DepartmentResult tests ──

class TestDepartmentResult:
    def test_initial_state(self):
        r = DepartmentResult()
        assert r.agent_results == {}
        assert r.summaries == {}
        assert r.briefing == ""
        assert r.failed_agent is None
        assert r.all_passed is True
        assert r.agent_questions == {}
        assert r.agent_comments == {}
        assert r.agent_confidence == {}


# ── PlanningDepartment unit tests ──

class TestPlanningDepartmentInit:
    @patch("departments.planning.AGENT_CLASSES", [])
    def test_empty_agent_classes(self):
        fm = MagicMock()
        dept = PlanningDepartment(fm)
        assert dept.agents == {}
        assert dept._agent_order == []

    def test_has_display_name(self):
        assert PlanningDepartment.display_name == "기획본부"


class TestCompressResult:
    @patch("departments.planning.call_llm", return_value="line1\nline2\nline3")
    def test_returns_stripped_compression(self, mock_llm):
        fm = MagicMock()
        dept = PlanningDepartment(fm)
        result = dept._compress_result("대상분석", "long output text")
        assert result == "line1\nline2\nline3"
        mock_llm.assert_called_once()
        # Verify it used _COMPRESS_SYSTEM
        assert mock_llm.call_args[0][2] == _COMPRESS_SYSTEM

    @patch("departments.planning.call_llm", side_effect=Exception("API error"))
    def test_fallback_on_error(self, mock_llm):
        fm = MagicMock()
        dept = PlanningDepartment(fm)
        result = dept._compress_result("대상분석", "line A\nline B\nline C\nline D")
        # Should fallback to first 3 non-empty lines
        assert "line A" in result
        assert "line B" in result
        assert "line C" in result

    @patch("departments.planning.call_llm", return_value="summary")
    def test_truncates_long_input(self, mock_llm):
        fm = MagicMock()
        dept = PlanningDepartment(fm)
        long_text = "x" * 1500
        dept._compress_result("대상분석", long_text)
        # The user msg should contain max 800 chars of result
        user_arg = mock_llm.call_args[0][3]
        assert len(user_arg) < 900  # 800 + agent name prefix


class TestGenerateBriefing:
    @patch("departments.planning.call_llm", return_value="strategic briefing text")
    def test_returns_briefing(self, mock_llm):
        fm = MagicMock()
        dept = PlanningDepartment(fm)
        result = DepartmentResult()
        result.summaries = {
            "대상_분석": "summary 1",
            "경쟁_분석": "summary 2",
        }
        briefing = dept._generate_briefing(result)
        assert briefing == "strategic briefing text"
        assert mock_llm.call_args[0][2] == _BRIEFING_SYSTEM


# ── ConceptPlanner multi-step tests ──

class TestConceptPlannerMultiStep:
    def test_has_no_steps_single_call_mode(self):
        """ConceptPlanner returns empty steps — single-call mode (Groq RPM 이슈로 비활성화)."""
        agent = ConceptPlannerAgent()
        assert agent.get_steps() == []

    @patch("agents.base_agent.call_llm")
    def test_single_call_mode_calls_llm_once(self, mock_llm):
        """ConceptPlanner.run() should call LLM once in single-call mode."""
        mock_llm.return_value = "step output"

        agent = ConceptPlannerAgent()
        context = {
            "대상자": {"이름": "Test"},
            "대상_분석": "analysis",
            "경쟁_분석": "competition",
            "플랫폼_추천": "platform",
        }
        result = agent.run(context)

        assert mock_llm.call_count == 1
        assert result == "step output"

    @patch("agents.base_agent.call_llm")
    def test_multi_step_strips_foreign_chars(self, mock_llm):
        """Multi-step results should have foreign chars stripped."""
        mock_llm.return_value = "refined with erklänen and 技術"

        agent = ConceptPlannerAgent()
        context = {
            "대상자": {"이름": "T"},
            "대상_분석": "a",
            "경쟁_분석": "b",
            "플랫폼_추천": "c",
        }
        result = agent.run(context)

        assert "ä" not in result
        assert "技" not in result
        assert "術" not in result


# ── BaseAgent foreign char regex tests ──

class TestForeignCharRegex:
    def test_strips_accented_latin(self):
        assert _FOREIGN_CHAR_RE.sub("", "vidéos") == "vidos"

    def test_strips_cyrillic(self):
        assert _FOREIGN_CHAR_RE.sub("", "контент") == ""

    def test_strips_cjk(self):
        assert _FOREIGN_CHAR_RE.sub("", "分析技術") == ""

    def test_strips_japanese(self):
        assert _FOREIGN_CHAR_RE.sub("", "リアル") == ""

    def test_preserves_korean(self):
        text = "한국어 테스트 123 English"
        assert _FOREIGN_CHAR_RE.sub("", text) == text

    def test_preserves_basic_ascii(self):
        text = "Hello World 123 !@#$%"
        assert _FOREIGN_CHAR_RE.sub("", text) == text


# -- _judge_quality tests --

class TestJudgeQuality:
    def test_good_score_passes(self):
        fm = MagicMock()
        dept = PlanningDepartment(fm)
        with patch("departments.planning.call_llm") as mock_llm:
            mock_llm.return_value = '{"score": 80, "reason": "good"}'
            r = dept._judge_quality("대상분석", "test", {"대상자": {"이름": "t"}})
            assert r["score"] == 80

    def test_low_score_returns_dict(self):
        fm = MagicMock()
        dept = PlanningDepartment(fm)
        with patch("departments.planning.call_llm") as mock_llm:
            mock_llm.return_value = '{"score": 40, "reason": "generic"}'
            r = dept._judge_quality("대상분석", "test", {"대상자": {"이름": "t"}})
            assert r["score"] == 40

    def test_error_returns_none(self):
        fm = MagicMock()
        dept = PlanningDepartment(fm)
        with patch("departments.planning.call_llm") as mock_llm:
            mock_llm.side_effect = Exception("fail")
            r = dept._judge_quality("대상분석", "test", {"대상자": {"이름": "t"}})
            assert r is None

    def test_uses_groq_provider(self):
        fm = MagicMock()
        dept = PlanningDepartment(fm)
        with patch("departments.planning.call_llm") as mock_llm:
            mock_llm.return_value = '{"score": 75, "reason": "ok"}'
            dept._judge_quality("대상분석", "test", {"대상자": {"이름": "t"}})
            assert mock_llm.call_args[0][0] == "groq"
            assert mock_llm.call_args[0][1] == "llama-3.3-70b-versatile"

    def test_invalid_json_returns_none(self):
        fm = MagicMock()
        dept = PlanningDepartment(fm)
        with patch("departments.planning.call_llm") as mock_llm:
            mock_llm.return_value = "not json"
            r = dept._judge_quality("대상분석", "test", {"대상자": {"이름": "t"}})
            assert r is None
