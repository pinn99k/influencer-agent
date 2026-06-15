import pytest
import shutil
from pathlib import Path

from core.file_manager import FileManager
from core.config import OUTPUTS_DIR


INFLUENCER = "테스트_fm"
BASE = OUTPUTS_DIR / INFLUENCER


@pytest.fixture(autouse=True)
def cleanup():
    yield
    if BASE.exists():
        shutil.rmtree(BASE)


def test_ensure_dirs_creates_structure():
    fm = FileManager(INFLUENCER)
    assert (BASE / "산출물").exists()
    assert (BASE / ".system" / "ceo").exists()
    assert (BASE / ".system" / "agents").exists()
    assert (BASE / ".system" / "prompts").exists()
    assert (BASE / ".system" / "logs").exists()
    assert (BASE / "인수인계").exists()


def test_save_prompt_output():
    fm = FileManager(INFLUENCER)
    fm.save_prompt_output("대상분석", "# 테스트 프롬프트")
    path = BASE / ".system" / "prompts" / "대상분석.md"
    assert path.exists()
    assert path.read_text(encoding="utf-8") == "# 테스트 프롬프트"


def test_save_state():
    fm = FileManager(INFLUENCER)
    fm.save_state({"current_phase": "실행중", "current_agent": "대상분석"})
    path = BASE / ".system" / "ceo" / "state.md"
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "current_phase" in content
    assert "실행중" in content


def test_save_output_and_versioning():
    fm = FileManager(INFLUENCER)
    fm.save_output("01", "대상분석", "# v1 내용")
    fm.save_output("01", "대상분석", "# v2 내용")

    current = BASE / "산출물" / "01_대상분석.md"
    assert current.read_text(encoding="utf-8") == "# v2 내용"

    versions = list((BASE / "산출물" / ".versions").glob("01_대상분석_v*.md"))
    assert len(versions) == 1
    assert versions[0].read_text(encoding="utf-8") == "# v1 내용"


def test_save_raw_and_versioning():
    fm = FileManager(INFLUENCER)
    fm.save_raw("대상분석", "raw v1")
    fm.save_raw("대상분석", "raw v2")

    raw_path = BASE / ".system" / "agents" / "대상분석" / "raw_output.md"
    assert raw_path.read_text(encoding="utf-8") == "raw v2"

    versions = list((BASE / ".system" / "agents" / "대상분석" / ".versions").glob("*.md"))
    assert len(versions) == 1


def test_save_briefing_unique_filename():
    fm = FileManager(INFLUENCER)
    fm.save_briefing(5, "# 브리핑 1")
    fm.save_briefing(5, "# 브리핑 2")

    briefings = list((BASE / ".system" / "briefings").glob("*.md"))
    assert len(briefings) == 2


def test_save_handover():
    fm = FileManager(INFLUENCER)
    fm.save_handover("# 인수인계 내용")
    files = list((BASE / "인수인계").glob("*.md"))
    assert len(files) == 1


def test_append_log():
    fm = FileManager(INFLUENCER)
    fm.append_log({"agent": "대상분석", "event": "start", "status": "🔄"})
    fm.append_log({"agent": "대상분석", "event": "done", "status": "✅"})

    log_files = list((BASE / ".system" / "logs").glob("*.jsonl"))
    assert len(log_files) == 1
    lines = log_files[0].read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
