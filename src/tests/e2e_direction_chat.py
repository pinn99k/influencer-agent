"""Integration test (real LLM) — direction + chat end-to-end with a control.

Proves the WHOLE chain, not mocked units:
  1) ChatEngine captures a direction the user states in chat
  2) it persists to 방향.md and reloads
  3) CEO._build_ceo_summary folds it into ceo_summary
  4) a real agent's output actually REFLECTS the direction
     -> control: same agent WITHOUT direction, compare keyword presence
         ("통과 != 검증": the with/without contrast is the real proof)

Run: cd src && python -m tests.e2e_direction_chat   (needs OPENAI_API_KEY)
Writes _e2e_direction_result.txt (keep until 핑구 confirms).
"""
import re
import shutil
from unittest.mock import MagicMock

from core.chat_engine import ChatEngine
from core.direction import DirectionProfile
from core.file_manager import FileManager
from core.config import OUTPUTS_DIR
from agents.ceo import CEO
from agents.agent_context import build_context
from agents.concept_planner import ConceptPlannerAgent

NAME = "통합테스트_방향"
KEYWORDS = ["연습", "프로필"]   # direction theme the output should reflect

_SUBJECT = {
    "이름": NAME, "직업": "헤어 디자이너", "특기": "컬러·펌",
    "성격": "차분하고 설명을 잘함", "타겟연령대": "20-30대 여성",
    "SNS경험": "인스타 팔로워 400명", "목표": "6개월 내 팔로워 1만",
}
_STUB_SUBJECT_ANALYSIS = "## 대상 분석 결과\n강점: 컬러 전문성, 차분한 설명력. 약점: 카메라 경험 부족."
_STUB_COMPETITION = "## 경쟁 분석 결과\n유사 헤어 크리에이터 다수, 비포애프터 포맷이 강세."
_STUB_PLATFORM = "## 플랫폼 추천 결과\n1순위 인스타 릴스, 2순위 유튜브 쇼츠."


def _base_context():
    return {
        "대상자": dict(_SUBJECT),
        "대상_분석": _STUB_SUBJECT_ANALYSIS,
        "경쟁_분석": _STUB_COMPETITION,
        "플랫폼_추천": _STUB_PLATFORM,
    }


def _run_concept(context):
    agent = ConceptPlannerAgent()
    scoped = build_context("컨셉기획", context)
    return agent.run(scoped)


def _kw_hits(text):
    return [k for k in KEYWORDS if k in text]


def main():
    report = []
    score = {}

    # ---- 1) chat captures direction ----
    fm = FileManager(NAME)
    chat = ChatEngine(fm)
    chat.start()
    r = chat.reply("콘텐츠는 연습영상 위주로 가고, 인스타 프로필 꾸미기에 집중하고 싶어")
    captured = r.captured_direction.strip()
    score["1_capture"] = bool(captured)
    report.append(f"[1] 채팅 방향 포착: {'PASS' if captured else 'FAIL'} -> '{captured}'")

    # ---- 2) persist + reload ----
    direction_text = captured or "콘텐츠: 연습영상 위주, 인스타 프로필 꾸미기"
    fm.save_direction(DirectionProfile(content_focus=direction_text).to_markdown(NAME))
    reloaded = fm.load_direction()
    score["2_persist"] = bool(reloaded and direction_text[:6] in reloaded)
    report.append(f"[2] 방향.md 저장+로드: {'PASS' if score['2_persist'] else 'FAIL'}")

    # ---- 3) ceo_summary injection (real LLM) ----
    ceo = CEO(fm, dry_run=False)
    ctx = _base_context()
    ceo._load_direction(ctx)
    ceo._build_ceo_summary(ctx)
    summary = ctx.get("ceo_summary", "")
    inj = any(k in summary for k in KEYWORDS) or (direction_text[:6] in summary)
    score["3_summary_injection"] = inj
    report.append(f"[3] ceo_summary 주입: {'PASS' if inj else 'FAIL'} (len={len(summary)})")

    # ---- 4) agent reflects direction vs control (real LLM) ----
    with_dir = _run_concept(ctx)                       # has 방향 via ceo_summary
    ctrl_ctx = _base_context()                         # NO direction, NO ceo_summary
    without_dir = _run_concept(ctrl_ctx)

    hits_with = _kw_hits(with_dir)
    hits_without = _kw_hits(without_dir)
    reflects = len(hits_with) > 0
    contrast = len(hits_with) > len(hits_without)
    score["4_agent_reflects"] = reflects
    score["4_contrast"] = contrast
    report.append(f"[4] 에이전트 반영: {'PASS' if reflects else 'FAIL'} "
                  f"(방향키워드 with={hits_with} vs without={hits_without})")
    report.append(f"    대조군 우위(with>without): {'PASS' if contrast else 'WEAK'}")

    # ---- 5) hygiene: foreign chars ----
    foreign = re.findall(r"[一-鿿぀-ヿ]", with_dir)
    score["5_no_foreign"] = (len(foreign) == 0)
    report.append(f"[5] 외래문자(한자/가나) 0개: {'PASS' if not foreign else f'FAIL({len(foreign)})'}")

    # ---- score ----
    weights = {"1_capture": 20, "2_persist": 15, "3_summary_injection": 25,
               "4_agent_reflects": 25, "4_contrast": 10, "5_no_foreign": 5}
    total = sum(w for k, w in weights.items() if score.get(k))
    report.append("")
    report.append(f"=== 통합테스트 점수: {total}/100 ===")
    for k, w in weights.items():
        report.append(f"  {k}: {'+' + str(w) if score.get(k) else '0'} / {w}")

    out = "\n".join(report)
    print(out)
    with open("_e2e_direction_result.txt", "w", encoding="utf-8") as f:
        f.write(out + "\n\n--- with_direction concept (head) ---\n" + with_dir[:1200]
                + "\n\n--- without_direction concept (head) ---\n" + without_dir[:1200])

    if (OUTPUTS_DIR / NAME).exists():
        shutil.rmtree(OUTPUTS_DIR / NAME)
    return total


if __name__ == "__main__":
    main()
