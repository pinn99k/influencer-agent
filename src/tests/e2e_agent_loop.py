"""Phase C 통합테스트 -- 실 LLM 도구 호출 루프 (수동 실행).

  cd src && python tests/e2e_agent_loop.py

가상 미용사로 CEO.run_autonomous를 gpt-4o tool-calling으로 완주시킨다.
검증: (1) 모델이 도구를 스스로 호출 (2) 워커 4개 모두 실행 (3) 루프 정지
(finish 또는 max_iter 내) (4) 산출물 + 최종리포트 생성. 결과는 stdout + 파일.
"""
import sys
import io
import shutil

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from agents.ceo import CEO
from core.file_manager import FileManager
from core.config import OUTPUTS_DIR

NAME = "자율통합_가상미용사"
SUBJECT = {
    "이름": NAME,
    "직업": "미용사 3년차",
    "특기": "헤어 컬러링, 단발 커트",
    "성격": "차분하고 설명을 잘함, 카메라는 조금 어색",
    "타겟연령대": "20-30대 여성",
    "SNS경험": "인스타 팔로워 200명, 거의 비활성",
    "목표": "6개월 내 인스타 팔로워 5천, 살롱 예약 문의 늘리기",
}


def main():
    base = OUTPUTS_DIR / NAME
    if base.exists():
        shutil.rmtree(base)

    fm = FileManager(NAME)
    ceo = CEO(fm, dry_run=False)
    ctx = {"대상자": dict(SUBJECT)}

    print("=" * 60)
    print("Phase C 통합테스트 -- 자율 도구 호출 루프 (gpt-4o)")
    print("=" * 60)
    result = ceo.run_autonomous(ctx)

    # 도구 호출 시퀀스 추출 (모델이 스스로 고른 순서)
    seq = []
    for m in result["messages"]:
        for tc in (m.get("tool_calls") or []):
            seq.append(tc["function"]["name"])

    print("\n--- 결과 ---")
    print("반복(iterations):", result["iterations"])
    print("정지(finished):", result["finished"])
    print("실행된 워커(ran):", result["ran"])
    print("도구 호출 순서:", " -> ".join(seq) if seq else "(없음)")

    # 산출물 확인
    deliv = base / "산출물"
    files = sorted(p.name for p in deliv.glob("*.md")) if deliv.exists() else []
    print("산출물 파일:", files)

    # 검증
    workers = {"대상분석", "경쟁분석", "플랫폼추천", "컨셉기획"}
    ran_all = workers.issubset(set(result["ran"]))
    used_tools = len(seq) > 0
    stopped = result["finished"] or result["iterations"] < 8
    has_outputs = len(files) >= 4

    print("\n--- 검증 ---")
    checks = {
        "도구를 스스로 호출": used_tools,
        "워커 4개 모두 실행": ran_all,
        "루프 정상 정지": stopped,
        "산출물 4개+ 생성": has_outputs,
    }
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")

    ok = all(checks.values())
    print("\n" + ("=" * 60))
    print("통합테스트:", "PASS" if ok else "FAIL")
    print("=" * 60)

    # 결과 보존 (핑구 확인 후 삭제)
    out_txt = OUTPUTS_DIR.parent / "_e2e_agent_loop_result.txt"
    it = result["iterations"]
    fin = result["finished"]
    ran = result["ran"]
    lines = [
        "iterations=" + str(it) + " finished=" + str(fin),
        "ran=" + str(ran),
        "seq=" + str(seq),
        "files=" + str(files),
        "checks=" + str(checks),
        "result=" + ("PASS" if ok else "FAIL"),
    ]
    out_txt.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    print("결과 보존:", out_txt)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
