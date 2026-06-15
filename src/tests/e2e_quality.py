"""Full 4-agent pipeline E2E quality measurement (gpt-4o).

Runs the planning pipeline for a virtual hairdresser, validates each output,
and scores each output 0-100 with an independent LLM judge.

Writes (in src/):
  _e2e_quality_summary.txt  -> short scores table (safe to read)
  _e2e_quality_full.txt     -> full markdown outputs

Run from src/:  python tests/e2e_quality.py
Requires OPENAI_API_KEY (+ SERPER_API_KEY) in src/.env
"""
import os
import sys
import time
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
os.chdir(SRC_DIR)

from agents import AGENT_CLASSES  # ordered list of agent classes
from core.llm_client import call_llm
from validators.output_validator import OutputValidator

# Virtual hairdresser subject (reflects 미용사 specifics from 실전적용 로드맵).
SUBJECT = {
    "이름": "김서연",
    "직업": "미용사",
    "특기": "탈색·명도컬러 전문, 얼굴형별 커트 컨설팅",
    "성격": "차분하고 섬세함, 말하기보다 손으로 보여주는 걸 편안해함",
    "타겟연령대": "20-30대 여성",
    "SNS경험": "개인 인스타그램 운영(팔로워 180명), 영상 촬영은 처음",
    "목표": "1개월 내 인스타그램 릴스/유튜브 쇼츠로 팔로워 500명 달성",
    "가용시간": "주 2-3회, 회당 30분 이내 (근무 중 틈틈이)",
}
SUBJECT_NAME = SUBJECT["이름"]

JUDGE_SYS = (
    "You are a strict quality auditor for an influencer agency's strategy deliverables. "
    "Score the Korean deliverable 0-100 on: concreteness (subject-specific, not generic), "
    "actionability (the hairdresser knows what to do next), and format correctness. "
    "Penalize generic advice, vague claims, missing subject name, and filler. "
    "Respond with ONLY a single integer 0-100."
)


def _judge(content, label):
    user = f"Deliverable: {label}\n\n---\n{content}\n---\n\nScore (integer 0-100 only):"
    try:
        raw = call_llm("openai", "gpt-4o", JUDGE_SYS, user, max_tokens=10)
        digits = "".join(c for c in str(raw) if c.isdigit())
        return int(digits[:3]) if digits else -1
    except Exception as e:  # noqa
        return f"err:{type(e).__name__}"


def main():
    context = {"대상자": SUBJECT}
    summary = []
    full = ["# E2E Quality Run (gpt-4o)\n"]

    for cls in AGENT_CLASSES:
        agent = cls()
        ck = cls.context_key
        dname = cls.display_name
        t0 = time.time()
        try:
            result = agent.run(context)
        except Exception as e:  # noqa
            summary.append(f"{dname}: RUN_ERROR {type(e).__name__}: {e}")
            full.append(f"\n## {dname} RUN_ERROR\n{e}\n")
            continue
        dt = time.time() - t0
        context[ck] = result

        try:
            vr = OutputValidator.validate(dname, result, SUBJECT_NAME)
            vstr = "PASS" if vr.passed else f"FAIL {vr.failed_rules}"
        except Exception as e:  # noqa
            vstr = f"val_err:{type(e).__name__}"

        score = _judge(result, dname)
        summary.append(f"{dname}: score={score} validate={vstr} len={len(result)} time={dt:.1f}s")
        full.append(f"\n{'='*60}\n## {dname}  (score={score}, validate={vstr})\n{'='*60}\n{result}\n")

    with open("_e2e_quality_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(summary) + "\n")
    with open("_e2e_quality_full.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(full))
    print("DONE")
    for line in summary:
        print(line)


if __name__ == "__main__":
    main()
