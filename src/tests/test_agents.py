import pytest
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from agents.subject_analyst import SubjectAnalystAgent
from agents.competition_analyst import CompetitionAnalystAgent
from agents.platform_recommender import PlatformRecommenderAgent
from agents.concept_planner import ConceptPlannerAgent
from tests.conftest import SAMPLE_CONTEXT, SAMPLE_SUBJECT




class TestSubjectAnalystAgent:
    def test_display_name(self):
        agent = SubjectAnalystAgent()
        assert agent.display_name == "대상분석"

    def test_get_context_keys(self):
        agent = SubjectAnalystAgent()
        assert agent.get_context_keys() == ["대상자"]

    def test_build_prompt_contains_subject(self):
        agent = SubjectAnalystAgent()
        prompt = agent.build_prompt(SAMPLE_CONTEXT)
        data = json.loads(prompt)
        assert "대상자" in data
        assert data["대상자"]["이름"] == "테스트크리에이터"

    def test_build_prompt_only_includes_context_keys(self):
        agent = SubjectAnalystAgent()
        prompt = agent.build_prompt(SAMPLE_CONTEXT)
        data = json.loads(prompt)
        assert "대상_분석" not in data  # 대상분석은 대상자만 필요


class TestCompetitionAnalystAgent:
    def test_display_name(self):
        agent = CompetitionAnalystAgent()
        assert agent.display_name == "경쟁분석"

    def test_get_context_keys(self):
        agent = CompetitionAnalystAgent()
        assert "대상자" in agent.get_context_keys()
        assert "대상_분석" in agent.get_context_keys()

    def test_build_prompt_includes_serper_results(self):
        agent = CompetitionAnalystAgent()
        ctx = {**SAMPLE_CONTEXT, "대상_분석": "# 대상 분석 결과"}
        serper_data = [{"title": "검색결과", "snippet": "내용", "link": "http://..."}]

        with patch("agents.competition_analyst.serper_client.search", return_value=serper_data):
            prompt = agent.build_prompt(ctx)
        data = json.loads(prompt)
        assert "serper_results" in data
        assert data["serper_results"][0]["title"] == "검색결과"

    def test_build_prompt_empty_serper_when_no_key(self):
        agent = CompetitionAnalystAgent()
        ctx = {**SAMPLE_CONTEXT, "대상_분석": "# 대상 분석 결과"}

        with patch("agents.competition_analyst.serper_client.search", return_value=[]):
            prompt = agent.build_prompt(ctx)
        data = json.loads(prompt)
        assert data["serper_results"] == []

    def test_run_calls_serper_then_llm(self):
        """경쟁분석 에이전트가 크리에이터 중심 다중 쿼리로 Serper를 호출하고 multi-step LLM을 호출한다."""
        agent = CompetitionAnalystAgent()
        ctx = {**SAMPLE_CONTEXT, "대상_분석": "# 대상 분석 결과"}

        with patch("agents.competition_analyst.serper_client.search", return_value=[]) as mock_search:
            with patch("agents.base_agent.call_llm", return_value="경쟁 분석 결과") as mock_llm:
                result = agent.run(ctx)

        # 다중 쿼리 전략: 최대 3회까지 search 호출 허용
        assert 1 <= mock_search.call_count <= 3, (
            f"search 호출 횟수는 1~3 사이여야 함. 실제: {mock_search.call_count}"
        )

        # 모든 쿼리를 합쳐서 직업·특기 키워드가 포함됐는지 확인
        all_queries = " ".join(call[0][0] for call in mock_search.call_args_list)
        assert "미용사" in all_queries, f"쿼리에 '미용사'가 없음. 쿼리: {all_queries}"
        assert "헤어컬러" in all_queries, f"쿼리에 '헤어컬러'가 없음. 쿼리: {all_queries}"

        # 크리에이터 중심 접미어가 적어도 하나의 쿼리에 포함됐는지 확인
        creator_keywords = ["유튜버", "크리에이터", "채널"]
        assert any(kw in all_queries for kw in creator_keywords), (
            f"크리에이터 키워드({creator_keywords})가 쿼리에 없음. 쿼리: {all_queries}"
        )

        # 단일 호출 모드 (get_steps()=[] — multi-step은 Groq RPM 이슈로 비활성화, 세션 25)
        assert mock_llm.call_count == 1, (
            f"경쟁분석 단일 호출 모드는 1회 LLM 호출이어야 함. 실제: {mock_llm.call_count}"
        )
        assert result == "경쟁 분석 결과"


class TestPlatformRecommenderAgent:
    def test_display_name(self):
        agent = PlatformRecommenderAgent()
        assert agent.display_name == "플랫폼추천"

    def test_get_context_keys(self):
        keys = PlatformRecommenderAgent().get_context_keys()
        assert "대상자" in keys
        assert "대상_분석" in keys
        assert "경쟁_분석" in keys

    def test_build_prompt_includes_all_keys(self):
        agent = PlatformRecommenderAgent()
        ctx = {
            **SAMPLE_CONTEXT,
            "대상_분석": "# 대상 분석",
            "경쟁_분석": "# 경쟁 분석",
        }
        prompt = agent.build_prompt(ctx)
        data = json.loads(prompt)
        assert "대상자" in data
        assert "대상_분석" in data
        assert "경쟁_분석" in data
        assert "플랫폼_추천" not in data  # 플랫폼추천은 이 키 불필요


class TestConceptPlannerAgent:
    def test_display_name(self):
        assert ConceptPlannerAgent().display_name == "컨셉기획"

    def test_get_context_keys_includes_all_prior(self):
        keys = ConceptPlannerAgent().get_context_keys()
        assert "대상자" in keys
        assert "대상_분석" in keys
        assert "경쟁_분석" in keys
        assert "플랫폼_추천" in keys

    def test_build_prompt_includes_platform(self):
        agent = ConceptPlannerAgent()
        ctx = {
            **SAMPLE_CONTEXT,
            "대상_분석": "# 대상 분석",
            "경쟁_분석": "# 경쟁 분석",
            "플랫폼_추천": "# 플랫폼 추천",
        }
        prompt = agent.build_prompt(ctx)
        data = json.loads(prompt)
        assert "플랫폼_추천" in data
