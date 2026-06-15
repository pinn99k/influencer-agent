import pytest
import shutil
from pathlib import Path

from core.file_manager import FileManager
from core.config import OUTPUTS_DIR
from agents.ceo import CEO, AGENT_ORDER
from tests.conftest import SAMPLE_CONTEXT, SAMPLE_SUBJECT


INFLUENCER = "테스트_ceo"
BASE = OUTPUTS_DIR / INFLUENCER
PROMPTS_DIR = BASE / ".system" / "prompts"


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if BASE.exists():
        shutil.rmtree(BASE)


@pytest.fixture
def ceo_dryrun():
    fm = FileManager(INFLUENCER)
    return CEO(fm, dry_run=True)


def test_dry_run_creates_prompts_directory(ceo_dryrun):
    context = {**SAMPLE_CONTEXT}
    ceo_dryrun.run(context)
    assert PROMPTS_DIR.exists()


def test_dry_run_creates_ceo_goal_prompt(ceo_dryrun):
    context = {**SAMPLE_CONTEXT}
    ceo_dryrun.run(context)
    path = PROMPTS_DIR / "ceo_goal_interpretation.md"
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert len(content) > 10  # 내용이 있어야 함


def test_dry_run_creates_all_agent_prompts(ceo_dryrun):
    context = {**SAMPLE_CONTEXT}
    ceo_dryrun.run(context)

    for agent_name in AGENT_ORDER:
        path = PROMPTS_DIR / f"{agent_name}.md"
        assert path.exists(), f"{agent_name} 프롬프트 파일 없음"


def test_dry_run_total_prompt_files(ceo_dryrun):
    context = {**SAMPLE_CONTEXT}
    ceo_dryrun.run(context)

    files = list(PROMPTS_DIR.glob("*.md"))
    # ceo_goal_interpretation + 4개 에이전트 = 5개
    assert len(files) == 5


def test_dry_run_does_not_call_llm(ceo_dryrun):
    """dry_run=True이면 LLM 호출 없어야 함."""
    from unittest.mock import patch
    context = {**SAMPLE_CONTEXT}

    with patch("core.llm_client.requests.post") as mock_post:
        ceo_dryrun.run(context)

    mock_post.assert_not_called()


def test_dry_run_saves_state(ceo_dryrun):
    context = {**SAMPLE_CONTEXT}
    ceo_dryrun.run(context)

    state_path = BASE / ".system" / "ceo" / "state.md"
    assert state_path.exists()
    content = state_path.read_text(encoding="utf-8")
    assert SAMPLE_SUBJECT["이름"] in content


def test_dry_run_does_not_modify_context(ceo_dryrun):
    """dry_run=True이면 context 분석 키가 None으로 유지되어야 함."""
    context = {**SAMPLE_CONTEXT}
    ceo_dryrun.run(context)

    assert context["대상_분석"] is None
    assert context["경쟁_분석"] is None
    assert context["플랫폼_추천"] is None
    assert context["컨셉_기획"] is None


def test_all_agents_have_context_key(ceo_dryrun):
    """All agents in AGENT_ORDER must have a non-empty context_key."""
    for name in AGENT_ORDER:
        agent = ceo_dryrun.agents[name]
        assert agent.context_key, f"{name} has no context_key"
