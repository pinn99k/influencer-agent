"""Gate Loop-002 — CEO.run() 전체 파이프라인으로 6섹션 종합 리포트 + plan 검증.

기존 e2e_quality.py 는 워커 4개만 직접 돌려 CEO._synthesize_final_report 를 안 거친다.
이 게이트는 CEO.run() 전체를 실행해 _finalize -> _synthesize_final_report 경로를
실제로 태우고, 산출물 최종리포트.md 가 폴백(구포맷)이 아닌 신규 6섹션인지,
plan_extractor 가 next_actions/kpi 를 실제로 뽑는지 단언한다.

실행:  cd src && python tests/gate_loop002.py
필요:  src/.env 의 OPENAI_API_KEY (+ SERPER_API_KEY)
"""
import os
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
os.chdir(SRC)
sys.stdout.reconfigure(encoding="utf-8")

from main import init_context
from core.file_manager import FileManager
from agents.ceo import CEO
from core.plan_extractor import extract_plan

SUBJECT = {
    "이름": "게이트이가은",
    "직업": "미용사",
    "특기": "탈색·명도컬러 전문, 얼굴형별 커트 컨설팅",
    "성격": "차분하고 섬세함, 손으로 보여주는 걸 편안해함",
    "타겟연령대": "20-30대 여성",
    "SNS경험": "개인 인스타그램(팔로워 180명), 영상 촬영은 처음",
    "목표": "1개월 내 릴스/쇼츠로 팔로워 500명",
    "가용시간": "주 2-3회, 회당 30분 이내",
}

SECTIONS = ["## 한 줄 결론", "## 핵심 결정 3가지", "## 강점과 기회",
            "## 4주 실행 로드맵", "## 지금 당장 할 3가지", "## 성공 지표"]


def main():
    name = SUBJECT["이름"]
    context = init_context(SUBJECT)
    fm = FileManager(name)
    ceo = CEO(fm)
    print("[GATE] CEO.run() 시작 — 워커4 + synthesis + 매니저 (수 분 소요)")
    ceo.run(context)

    base = Path(f"outputs/{name}/산출물")
    ft = (base / "최종리포트.md").read_text(encoding="utf-8")
    ct = (base / "04_컨셉기획.md").read_text(encoding="utf-8")

    print("\n[GATE] 최종리포트 6섹션 검증")
    missing = [s for s in SECTIONS if s not in ft]
    for s in SECTIONS:
        print(f"  [{'O' if s not in missing else 'X'}] {s}")
    is_fallback = ft.lstrip().startswith("# 최종 리포트")
    print(f"  폴백(구포맷) 여부: {is_fallback}")

    plan = extract_plan(ct, ft)
    print("\n[GATE] plan_extractor 추출")
    wk = [len(w["items"]) for w in plan["weeks"]]
    print(f"  weeks items: {wk}")
    print(f"  next_actions: {len(plan['next_actions'])} -> {plan['next_actions'][:2]}")
    print(f"  kpi: {len(plan['kpi'])} -> {plan['kpi'][:3]}")

    # 외래문자
    import re
    foreign = re.compile(r"[぀-ヿ一-鿿Ѐ-ӿ]")
    fc = len(foreign.findall(ft))
    print(f"\n[GATE] 최종리포트 외래문자: {fc}")

    ok = (not missing) and (not is_fallback) and plan["next_actions"] and plan["kpi"] and fc == 0
    print(f"\n[GATE RESULT] {'PASS' if ok else 'FAIL'}")
    if not ok:
        print("  실패 사유:",
              ("섹션누락 " + ",".join(missing) + " ") if missing else "",
              "폴백발생 " if is_fallback else "",
              "next_actions비음 " if not plan["next_actions"] else "",
              "kpi비음 " if not plan["kpi"] else "",
              f"외래문자{fc} " if fc else "")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
