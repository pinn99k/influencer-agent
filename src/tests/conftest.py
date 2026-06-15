import pytest
import sys
import shutil
from pathlib import Path

# src/ 를 sys.path에 추가 (cd src && pytest 실행 기준)
sys.path.insert(0, str(Path(__file__).parent.parent))


from core.config import PROMPTS_DIR
from agents import get_context_keys

_AGENT_PROMPT_FILES = [
    ("dept/planning/subject_analysis", "# 대상분석 프롬프트"),
    ("dept/planning/competition_analysis", "# 경쟁분석 프롬프트"),
    ("dept/planning/platform_recommendation", "# 플랫폼추천 프롬프트"),
    ("dept/planning/concept_planning", "# 컨셉기획 프롬프트"),
    ("ceo/goal_interpretation", "# CEO 목표 해석 프롬프트"),
    ("ceo/next_decision", "# CEO 다음 판단 프롬프트"),
]


@pytest.fixture(autouse=True)
def setup_prompt_files():
    """에이전트 초기화에 필요한 prompts/ 파일을 임시 생성 후 cleanup."""
    created = []
    for rel_path, content in _AGENT_PROMPT_FILES:
        path = PROMPTS_DIR / f"{rel_path}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(path)
    yield
    for path in created:
        if path.exists():
            path.unlink()


SAMPLE_SUBJECT = {
    "이름": "테스트크리에이터",
    "직업": "미용사",
    "특기": "헤어컬러",
    "성격": "내향적, 섬세함",
    "타겟연령대": "20대 여성",
    "SNS경험": "인스타그램 팔로워 200명",
    "목표": "6개월 내 유튜브 구독자 1,000명 달성",
}

def _build_sample_context():
    ctx = {"대상자": SAMPLE_SUBJECT}
    for key in get_context_keys():
        ctx[key] = None
    ctx["검증_결과"] = None
    ctx["보고_조건"] = None
    return ctx

SAMPLE_CONTEXT = _build_sample_context()
