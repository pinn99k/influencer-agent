import json
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.file_manager import FileManager
from core.config import OUTPUTS_DIR
from agents.ceo import CEO, AGENT_ORDER
from tests.conftest import SAMPLE_CONTEXT, SAMPLE_SUBJECT


INFLUENCER = "테스트_decide_next"
BASE = OUTPUTS_DIR / INFLUENCER


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if BASE.exists():
        shutil.rmtree(BASE)


@pytest.fixture
def ceo():
    fm = FileManager(INFLUENCER)
    c = CEO(fm, dry_run=False)
    c._init_state(SAMPLE_SUBJECT["이름"])
    return c


def _ctx_key(ceo_obj, display_name: str) -> str:
    """Get context_key from agent display_name via CEO's agents dict."""
    return ceo_obj.agents[display_name].context_key


def _make_llm_response(action: str, target: str = "", reason: str = "ok", condition: int = 0) -> str:
    return json.dumps(
        {"action": action, "target": target, "reason": reason, "condition": condition},
        ensure_ascii=False,
    )


class TestDecideNextComplete:
    def test_returns_complete_when_all_done(self, ceo):
        """모든 에이전트 완료 시 LLM 호출 없이 즉시 complete 반환."""
        context = {**SAMPLE_CONTEXT}
        for name in AGENT_ORDER:
            context[_ctx_key(ceo, name)] = "결과"

        with patch("core.llm_client.requests.post") as mock_post:
            result = ceo._decide_next(context)

        mock_post.assert_not_called()
        assert result["action"] == "complete"


class TestDecideNextSequential:
    def test_returns_first_remaining_agent(self, ceo):
        """남은 첫 번째 에이전트를 순서대로 반환."""
        context = {**SAMPLE_CONTEXT}
        result = ceo._decide_next(context)
        assert result["action"] == "run"
        assert result["target"] == AGENT_ORDER[0]

    def test_skips_completed_agents(self, ceo):
        """완료된 에이전트 건너뛰고 다음 순서 반환."""
        context = {**SAMPLE_CONTEXT}
        context[_ctx_key(ceo, "대상분석")] = "결과"
        result = ceo._decide_next(context)
        assert result["action"] == "run"
        assert result["target"] == "경쟁분석"

    def test_uses_llm_for_decision(self, ceo):
        """CEO LLM 판단 복원 — _decide_next가 LLM을 호출한다."""
        context = {**SAMPLE_CONTEXT}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": _make_llm_response("run", "대상분석")}}]
        }
        with patch("core.llm_client.get_cached", return_value=None), \
             patch("core.llm_client.set_cached"), \
             patch("core.llm_client.requests.post", return_value=mock_resp) as mock_post:
            result = ceo._decide_next(context)
        mock_post.assert_called_once()
        assert result["action"] == "run"
        assert result["target"] == "대상분석"
