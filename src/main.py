import sys
import io
import argparse

# Windows: stdin/stdout UTF-8 강제 (cp949 surrogate 에러 방지)
if sys.platform == "win32":
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )

from pathlib import Path
from core.file_manager import FileManager
from core.config import OUTPUTS_DIR
from agents.ceo import CEO
from agents import get_context_keys


FIELDS = [
    ("이름",       "크리에이터 이름 (가명 가능)"),
    ("직업",       "현재 직업 또는 전문 분야"),
    ("특기",       "잘하는 것 / 두드러지는 능력"),
    ("성격",       "외향/내향, 말하기 스타일 등"),
    ("타겟연령대", "주로 어필하고 싶은 연령대"),
    ("SNS경험",    "현재 운영 중인 채널/계정 현황"),
    ("목표",       "6개월~1년 내 달성하고 싶은 것"),
]


def collect_inputs() -> dict:
    """CLI에서 7개 필드 입력받아 대상자 dict 반환."""
    print("\n=== 인플루언서 에이전트 ===")
    print("대상자 정보를 입력하세요. (빈 칸 Enter → '정보 없음' 처리)\n")

    subject = {}
    for field, description in FIELDS:
        value = input(f"[{field}] {description}: ").strip()
        subject[field] = value if value else "정보 없음"

    # 목표 불명확 판정 (10자 미만)
    if len(subject.get("목표", "")) < 10:
        print("\n목표가 너무 짧습니다. 구체적으로 입력해주세요.")
        print("예) '유튜브 구독자 1만명 달성', '인스타그램 팔로워 5천명 + 협찬 1건'\n")
        subject["목표"] = input("[목표 재입력]: ").strip() or "정보 없음"

    return subject


def _load_subject_from_outputs(name: str) -> dict | None:
    """outputs/{name}/.system/ceo/state.md 또는 산출물에서 대상자 정보 복원 시도.

    가장 확실한 소스: outputs/{name}/산출물/ 내 01_대상분석.md 첫 줄에서 이름 추출.
    state.md에서 subject 정보 파싱이 어려우므로 최소한 이름만 복원.
    """
    base = OUTPUTS_DIR / name
    if not base.exists():
        return None
    # 최소 대상자 정보 — 이름만이라도 복원
    return {"이름": name}


def init_context(subject: dict) -> dict:
    """context dict 초기화 — 에이전트 키는 레지스트리에서 파생."""
    ctx = {"대상자": subject}
    for key in get_context_keys():
        ctx[key] = None
    ctx["검증_결과"] = None
    ctx["보고_조건"] = None
    return ctx


def run_interview_cli(engine) -> dict:
    """CEO 대화형 인터뷰 CLI 루프 -> subject dict 반환."""
    print("\n=== 인플루언서 에이전트 — 첫 상담 ===\n")
    print(f"CEO: {engine.start()}\n")

    while True:
        user = input("> ").strip()
        response = engine.reply(user)
        print(f"\nCEO: {response.message}\n")
        if response.type == "summary":
            break

    corrections = 0
    while True:
        ans = input("확인하시려면 Enter, 수정할 내용이 있으면 입력하세요.\n> ").strip()
        if not ans or corrections >= 3:
            subject = engine.confirm(True)
            break
        subject = engine.confirm(False, ans)
        corrections += 1
        print("\n[수정 반영]")
        for k, v in subject.items():
            print(f"- {k}: {v}")
        print()

    print("\n확인되었습니다. 분석을 시작합니다!\n")
    return subject


def main():
    parser = argparse.ArgumentParser(description="인플루언서 에이전트")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Spiral 0-A: API 호출 없이 프롬프트 파일 출력만",
    )
    parser.add_argument(
        "--reanalyze",
        action="store_true",
        help="재분석 모드: 기존 산출물 + 성과/피드백 기반 부분 재실행",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="대상자 이름 (--reanalyze 시 필수, 기존 outputs 폴더명과 일치해야 함)",
    )
    parser.add_argument(
        "--init-feedback",
        action="store_true",
        help="피드백.md 템플릿만 생성 (--name 필수)",
    )
    parser.add_argument(
        "--init-performance",
        action="store_true",
        help="성과기록.md 템플릿만 생성 (--name 필수)",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="기존 7필드 폼 입력 모드 (대화형 인터뷰 대신)",
    )
    parser.add_argument(
        "--interview",
        action="store_true",
        help="CEO 대화형 인터뷰로 정보 수집 (기본값)",
    )
    args = parser.parse_args()

    # ── 템플릿 생성 전용 모드 ──
    if args.init_feedback:
        if not args.name:
            print("오류: --init-feedback 사용 시 --name 필수")
            sys.exit(1)
        fm = FileManager(args.name)
        path = fm.init_feedback_template()
        print(f"피드백 템플릿: {path}")
        return

    if args.init_performance:
        if not args.name:
            print("오류: --init-performance 사용 시 --name 필수")
            sys.exit(1)
        fm = FileManager(args.name)
        path = fm.init_performance_record()
        print(f"성과기록 템플릿: {path}")
        return

    # ── 재분석 모드 ──
    if args.reanalyze:
        if not args.name:
            print("오류: --reanalyze 사용 시 --name 필수")
            sys.exit(1)

        subject = _load_subject_from_outputs(args.name)
        if subject is None:
            print(f"오류: outputs/{args.name} 폴더가 존재하지 않습니다.")
            print("먼저 1차 실행을 완료하세요.")
            sys.exit(1)

        context = init_context(subject)
        fm = FileManager(args.name)
        ceo = CEO(fm)

        print(f"\n=== 재분석 모드 ===")
        print(f"대상자: {args.name}")

        perf = fm.load_performance_record()
        feedback = fm.load_feedback()
        print(f"성과기록: {'있음' if perf else '없음'}")
        print(f"피드백: {'있음' if feedback else '없음'}")
        print()

        ceo.run_reanalyze(context)

        print(f"\n재분석 완료. outputs/{args.name}/산출물/ 에서 결과를 확인하세요.")
        return

    # ── 일반 실행 모드 ──
    if args.legacy or args.dry_run:
        subject = collect_inputs()          # 기존 7필드 폼 (dry-run은 API 없어 인터뷰 불가)
    else:
        from core.interview_engine import InterviewEngine
        subject = run_interview_cli(InterviewEngine())
    context = init_context(subject)

    fm = FileManager(subject["이름"])
    ceo = CEO(fm, dry_run=args.dry_run)

    if args.dry_run:
        print(f"\n[dry_run 모드] API 호출 없이 프롬프트 파일을 저장합니다.")
        print(f"저장 위치: outputs/{subject['이름']}/.system/prompts/\n")

    ceo.run(context)

    if args.dry_run:
        print(f"\n완료. outputs/{subject['이름']}/.system/prompts/ 에서 프롬프트를 확인하세요.")
        print("각 .md 파일을 Claude/GPT에 붙여넣어 품질을 직접 테스트할 수 있습니다.")
    else:
        # 1차 실행 완료 후 성과기록 + 피드백 템플릿 자동 생성
        perf_path = fm.init_performance_record()
        feedback_path = fm.init_feedback_template()
        print(f"\n성과기록 템플릿: {perf_path}")
        print(f"피드백 템플릿: {feedback_path}")
        print("성과 데이터를 기록한 후 --reanalyze로 재분석할 수 있습니다.")


if __name__ == "__main__":
    main()
