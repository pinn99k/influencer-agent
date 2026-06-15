"""
실 인플루언서 적용 스크립트 (Spiral 2)
======================================
사용법:
  cd src
  py run_influencer.py

subject 딕셔너리에 실제 인플루언서 정보를 채워서 실행한다.
main.py의 input() 방식 대신 직접 데이터를 주입하므로
Windows 한글 인코딩 문제 없이 동작한다.
"""
import sys
import time

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from core.file_manager import FileManager
from agents.ceo import CEO
from agents import get_context_keys


# ── 여기에 실 인플루언서 정보 입력 ──────────────────────────────
subject = {
    "이름":       "테스트크리에이터",          # 실제 이름 또는 가명
    "직업":       "미용사",                   # 현재 직업/전문분야
    "특기":       "헤어컬러링, 트렌드 스타일링",  # 잘하는 것
    "성격":       "내향적, 꼼꼼함, 영상보단 글 편함",  # 성격/스타일
    "타겟연령대": "20대 여성",                 # 어필 대상
    "SNS경험":    "인스타그램 팔로워 200명, 유튜브 없음",  # 현재 현황
    "목표":       "6개월 내 유튜브 구독자 1,000명 달성, 협찬 1건 유치",  # 구체적 목표
}
# ─────────────────────────────────────────────────────────────────


def init_context(subject: dict) -> dict:
    ctx = {"대상자": subject}
    for key in get_context_keys():
        ctx[key] = None
    ctx["검증_결과"] = None
    ctx["보고_조건"] = None
    return ctx


def main():
    print("\n=== 인플루언서 에이전트 실행 ===")
    print(f"대상자: {subject['이름']}")
    print(f"목표: {subject['목표']}")
    print("=" * 40)

    context = init_context(subject)
    fm = FileManager(subject["이름"])
    ceo = CEO(fm, dry_run=False)

    start = time.time()
    ceo.run(context)
    elapsed = time.time() - start

    print(f"\n완료! 소요시간: {elapsed:.1f}초")
    name = subject["이름"]
    print(f"산출물 위치: outputs/{name}/산출물/")
    print(f"  - 01_대상분석.md")
    print(f"  - 02_경쟁분석.md")
    print(f"  - 03_플랫폼추천.md")
    print(f"  - 04_컨셉기획.md")
    print(f"  - 최종리포트.md")


if __name__ == "__main__":
    main()
