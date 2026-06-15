import pytest
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from agents.base_agent import BaseAgent
from core.config import PROMPTS_DIR, KNOWLEDGE_DIR


TEMP_PROMPT_DIR = PROMPTS_DIR / "테스트부서"


class ConcreteAgent(BaseAgent):
    display_name = "테스트에이전트"
    prompt_file = "테스트부서/테스트프롬프트"
    knowledge_dir = ""
    context_key = "테스트_결과"
    output_prefix = "99"
    output_label = "테스트 결과"

    def build_prompt(self, context: dict) -> str:
        return "테스트 유저 프롬프트"

    def get_context_keys(self) -> list[str]:
        return ["대상자"]


class ConcreteAgentWithKnowledge(ConcreteAgent):
    knowledge_dir = "테스트_지식"


@pytest.fixture
def sample_prompt_file():
    TEMP_PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    prompt_path = TEMP_PROMPT_DIR / "테스트프롬프트.md"
    prompt_path.write_text("# 테스트 시스템 프롬프트\n역할: 테스트", encoding="utf-8")
    yield prompt_path
    shutil.rmtree(TEMP_PROMPT_DIR, ignore_errors=True)


def test_load_template_reads_prompt_file(sample_prompt_file):
    agent = ConcreteAgent()
    assert "테스트 시스템 프롬프트" in agent.system_prompt


def test_missing_prompt_file_raises_file_not_found():
    with pytest.raises(FileNotFoundError, match="프롬프트 파일 없음"):
        ConcreteAgent()  # 파일 없으면 __init__ 시 에러


def test_load_knowledge_empty_when_no_dir(sample_prompt_file):
    agent = ConcreteAgent()  # knowledge_dir = ""
    # system_prompt = template만 (knowledge 없음)
    assert agent.system_prompt == "# 테스트 시스템 프롬프트\n역할: 테스트"


def test_load_knowledge_empty_when_dir_not_exist(sample_prompt_file):
    agent = ConcreteAgentWithKnowledge()
    # knowledge/테스트_지식/ 없음 → 빈 문자열
    assert "테스트 시스템 프롬프트" in agent.system_prompt


def test_load_knowledge_merges_files(sample_prompt_file, tmp_path):
    knowledge_base = KNOWLEDGE_DIR / "테스트_지식"
    knowledge_base.mkdir(parents=True, exist_ok=True)
    (knowledge_base / "a_지식.md").write_text("# 지식A", encoding="utf-8")
    (knowledge_base / "b_지식.md").write_text("# 지식B", encoding="utf-8")

    try:
        agent = ConcreteAgentWithKnowledge()
        assert "지식A" in agent.system_prompt
        assert "지식B" in agent.system_prompt
        # 알파벳순 정렬 확인 (a_ 먼저)
        assert agent.system_prompt.index("지식A") < agent.system_prompt.index("지식B")
    finally:
        shutil.rmtree(knowledge_base, ignore_errors=True)


def test_run_calls_llm(sample_prompt_file):
    agent = ConcreteAgent()
    context = {"대상자": {"이름": "테스트"}}

    with patch("agents.base_agent.call_llm", return_value="LLM 응답") as mock_llm:
        result = agent.run(context)

    assert result == "LLM 응답"
    mock_llm.assert_called_once()
    call_args = mock_llm.call_args
    assert call_args[0][2] == agent.system_prompt  # system 인자
    assert call_args[0][3] == "테스트 유저 프롬프트"  # user 인자


def test_abstract_methods_enforced():
    """BaseAgent는 ABC — 추상 메서드 없으면 인스턴스 생성 불가."""
    with pytest.raises(TypeError):
        BaseAgent()  # type: ignore
