# -*- coding: utf-8 -*-
"""사용자 여정 평가 (e2e) — 실제 사용자가 산출물만 보고 한 달을 운영할 수 있는가.

핵심: AI 기준 "섹션 존재"가 아니라, 비전문가 사용자 입장에서 "각 단계를 실제로
따라 할 수 있는가"를 0/1/2로 채점한다. LLM이 대상자 본인 역할을 연기하며 평가.

실행: cd src && python tests/e2e_user_journey.py [이름]   (기본: 예으니)
필요: src/.env 의 OPENAI_API_KEY
"""
import sys, json, re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv()
from core.llm_client import call_llm
DEFAULT_PROVIDER, DEFAULT_MODEL = "openai", "gpt-4o"

STEPS = [
    "프로필/바이오 세팅",
    "오늘(1일차) 뭘 찍을지 정하기",
    "그 영상을 어떻게 구성할지 (훅/순서/길이)",
    "실제 촬영 (장비/장소/방법)",
    "편집 (앱/자막/컷)",
    "캡션 쓰기",
    "해시태그 넣기",
    "언제 올릴지",
    "이번 주 나머지 + 4주 계획 따라가기",
    "성과 확인 + 다음에 뭘 바꿀지",
]

JUDGE_SYSTEM = """당신은 28세 미용 일을 하는 사람입니다. SNS는 거의 안 해봤고 영상 편집도 초보입니다.
방금 컨설팅에서 '전략 보고서'와 '콘텐츠 기획서'를 받았고, 이걸 보고 진짜로 인스타그램을 시작하려 합니다.
당신은 AI 평가자가 아니라, 실제로 따라 하려는 초보 사용자입니다. 냉정하고 정직하게 답하세요.

아래 10단계를 '받은 문서만' 보고 실제로 할 수 있는지 판단합니다.
점수: 0 = 뭘 어떻게 하라는지 모르겠다(막힘) / 1 = 대충 알겠지만 빈 곳이 있어 멈칫 / 2 = 바로 따라 할 수 있다.
초보 입장에서 "이건 어떻게?" 싶으면 1이나 0. 후하게 주지 말 것.

반드시 JSON만 출력:
{"steps":[{"no":1,"name":"...","score":0,"blocker":"막힌 이유 한 줄(2점이면 빈 문자열)"}, ...],
 "total": 정수합(0~20),
 "verdict":"이 문서만으로 한 달 운영 가능한지 한 줄 솔직 답"}"""


def deterministic_checks(report: str, concept: str, name: str) -> list:
    issues = []
    if name not in report:
        issues.append(f"이름 누락/오염: 리포트에 '{name}' 없음")
    if "정보 없음" in concept or "정보 없음" in report:
        issues.append("플레이스홀더 '정보 없음' 노출")
    eng = re.findall(r"[A-Za-z]{4,}", concept)
    bad = [w for w in eng if w.lower() not in ("week", "capcut", "bgm", "cta", "sns", "vlog")]
    if bad:
        issues.append(f"번역 안 된 영어 표현: {sorted(set(bad))[:5]}")
    seg = concept.split("추천 해시태그")[1].split("캡션")[0] if "추천 해시태그" in concept else ""
    nich = next((l for l in seg.splitlines() if "니치" in l), "")
    if nich.count("#") < 5:
        issues.append(f"니치 해시태그 5개 미만 ({nich.count('#')}개)")
    if "구성:" not in concept:
        issues.append("영상 아이디어에 구성(훅/핵심/마무리) 없음")
    return issues


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    name = sys.argv[1] if len(sys.argv) > 1 else "예으니"
    base = Path(__file__).resolve().parent.parent / "outputs" / name / "산출물"
    report = (base / "최종리포트.md").read_text(encoding="utf-8")
    concept = (base / "04_컨셉기획.md").read_text(encoding="utf-8")

    print(f"===== 사용자 여정 평가: {name} =====\n")
    det = deterministic_checks(report, concept, name)
    print("[결정론적 체크]")
    if det:
        for d in det:
            print("  FAIL:", d)
    else:
        print("  통과 (이름/플레이스홀더/영어/해시태그/구성)")

    user_msg = f"=== 전략 보고서 ===\n{report}\n\n=== 콘텐츠 기획서 ===\n{concept}"
    raw = call_llm(DEFAULT_PROVIDER, DEFAULT_MODEL, JUDGE_SYSTEM, user_msg, max_tokens=1500)
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```")[1]
        if s.startswith("json"):
            s = s[4:]
    st, en = s.find("{"), s.rfind("}") + 1
    data = json.loads(s[st:en])

    print("\n[사용자 여정 점수 — 본인 역할 연기]")
    for step in data["steps"]:
        mark = {0: "X", 1: "~", 2: "O"}.get(step["score"], "?")
        line = f"  [{mark}] {step['no']}. {step['name']}: {step['score']}"
        if step.get("blocker"):
            line += f"  -> {step['blocker']}"
        print(line)
    total = data["total"]
    print(f"\n총점: {total}/20")
    print("한줄 평결:", data["verdict"])

    zeros = [s for s in data["steps"] if s["score"] == 0]
    passed = (total >= 16) and (not zeros) and (not det)
    print(f"\n판정: {'확정 가능 (PASS)' if passed else '미완성 (FAIL) — 보완 필요'}")
    if det:
        print("  사유: 결정론적 결함", len(det), "건")
    if zeros:
        print("  사유: 막힌 단계", [s["no"] for s in zeros])
    return passed


if __name__ == "__main__":
    main()
