"""
E2E test script for Gemini 2.0 Flash integration.
Run from src/ directory: py tests/e2e_gemini.py

Steps:
  1. API connection test - single LLM call
  2. Single agent test (SubjectAnalystAgent only)
  3. Full CEO E2E (all 4 agents)

Each step prints PASS/FAIL with timing.
Stops immediately on first failure.
"""

import sys
import os
import time
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# Ensure src/ is on the import path and cwd is src/ regardless of launch location
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
os.chdir(SRC_DIR)

# ── test context ──────────────────────────────────────────────────────────────

TEST_CONTEXT = {
    "대상자": {
        "이름": "김민수",
        "직업": "미용사 수습생",
        "특기": "블리치, 헤어 컬러링",
        "성격": "내향적, 섬세한 성격, 손재주 좋음",
        "타겟": "20대 여성",
        "SNS경험": "인스타그램 팔로워 300명",
        "목표": "1년 안에 팔로워 10,000명 + 미용 관련 협찬 받기",
    }
}

SUBJECT_NAME = TEST_CONTEXT["대상자"]["이름"]

# ── helpers ───────────────────────────────────────────────────────────────────

def _ok(step: str, elapsed: float, detail: str = "") -> None:
    msg = f"Step {step} PASS: {detail} ({elapsed:.1f}s)"
    print(f"\n[PASS] {msg}")


def _fail(step: str, elapsed: float, err: Exception | str) -> None:
    print(f"\n[FAIL] Step {step} FAIL ({elapsed:.1f}s): {err}")


def _section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── Step 1: API connection ────────────────────────────────────────────────────

def step1_api_connection() -> bool:
    _section("Step 1: Gemini API 연결 테스트")
    from core.llm_client import call_llm, DEFAULT_PROVIDER, DEFAULT_MODEL

    t0 = time.time()
    try:
        response = call_llm(
            provider=DEFAULT_PROVIDER,
            model=DEFAULT_MODEL,
            system="You are a helpful assistant. Reply in one sentence.",
            user="Say 'API connection successful' in Korean.",
        )
        elapsed = time.time() - t0
        if not response or len(response.strip()) == 0:
            raise ValueError("Empty response received from LLM")
        print(f"  Provider : {DEFAULT_PROVIDER}")
        print(f"  Model    : {DEFAULT_MODEL}")
        print(f"  Response : {response.strip()[:120]}")
        _ok("1", elapsed, f"LLM responded in {elapsed:.1f}s")
        return True
    except EnvironmentError as e:
        elapsed = time.time() - t0
        _fail("1", elapsed, f"API 키 미설정 — {e}")
        print("  힌트: .env 파일에 GEMINI_API_KEY=<your_key> 추가 후 재실행")
        return False
    except Exception as e:
        elapsed = time.time() - t0
        _fail("1", elapsed, e)
        return False


# ── Step 2: SubjectAnalystAgent standalone ────────────────────────────────────

def step2_subject_analyst() -> bool:
    _section("Step 2: 대상분석 에이전트 단독 실행")
    import re
    from agents.subject_analyst import SubjectAnalystAgent
    from validators.output_validator import OutputValidator

    t0 = time.time()
    try:
        agent = SubjectAnalystAgent()
        print(f"  Agent    : {agent.display_name}")
        print(f"  Prompt   : {agent.prompt_file}")
        print(f"  Running LLM call…")

        result = agent.run(TEST_CONTEXT)
        elapsed = time.time() - t0

        # CJK check
        cjk_found = re.findall(r"[一-鿿぀-ゟ゠-ヿ㐀-䶿]", result)
        cjk_count = len(cjk_found)

        # Validator check
        val = OutputValidator.validate("대상분석", result, SUBJECT_NAME)

        print(f"\n  --- 출력 미리보기 (처음 400자) ---")
        print(result[:400])
        print(f"  --- 끝 ---")
        print(f"\n  CJK 문자 수  : {cjk_count}")
        print(f"  Validator    : {'PASS' if val.passed else 'FAIL'}")
        if not val.passed:
            for rule in val.failed_rules:
                print(f"    x {rule}")

        if not val.passed:
            elapsed = time.time() - t0
            _fail("2", elapsed, f"OutputValidator FAIL — {', '.join(val.failed_rules)}")
            return False

        if cjk_count > 0:
            elapsed = time.time() - t0
            _fail("2", elapsed, f"CJK 문자 {cjk_count}개 잔존 — BaseAgent._FOREIGN_CHAR_RE 확인 필요")
            return False

        _ok("2", elapsed, f"OutputValidator PASS, CJK 0개, 출력 {len(result)}자")
        return True

    except Exception as e:
        elapsed = time.time() - t0
        _fail("2", elapsed, e)
        return False


# ── Step 3: Full CEO E2E ──────────────────────────────────────────────────────

def step3_ceo_e2e() -> bool:
    _section("Step 3: CEO 전체 E2E (4개 에이전트 순차 실행)")
    import copy
    from core.file_manager import FileManager
    from agents.ceo import CEO
    from agents import get_agent_order, AGENT_CLASSES
    from validators.output_validator import OutputValidator

    context = copy.deepcopy(TEST_CONTEXT)
    t0 = time.time()

    try:
        fm = FileManager(SUBJECT_NAME)
        ceo = CEO(file_manager=fm, dry_run=False)

        agent_order = get_agent_order()
        print(f"  실행 순서: {' → '.join(agent_order)}")
        print(f"  출력 위치: {fm.base / '산출물'}")
        print()

        ceo.run(context)
        elapsed = time.time() - t0
        _agent_times: dict[str, float] = {}  # timing unavailable (dept delegation)

        # ── result analysis ──

        # Check chairman report triggered
        if ceo._state_mgr.current_phase == "회장보고대기":
            _fail("3", elapsed, "CEO가 회장보고 상태로 종료됨 — 에이전트 검증 실패 또는 rate limit")
            return False

        # Check all 4 agents completed
        agent_classes_map = {cls.display_name: cls for cls in AGENT_CLASSES}
        failed_agents = []
        for name in agent_order:
            cls = agent_classes_map[name]
            if not context.get(cls.context_key):
                failed_agents.append(name)

        if failed_agents:
            _fail("3", elapsed, f"미완료 에이전트: {', '.join(failed_agents)}")
            return False

        # Check output files
        output_dir = fm.base / "산출물"
        expected_files = []
        for cls in AGENT_CLASSES:
            expected_files.append(f"{cls.output_prefix}_{cls.display_name}.md")
        expected_files.append("최종리포트.md")

        missing_files = []
        for fname in expected_files:
            fpath = output_dir / fname
            if not fpath.exists():
                missing_files.append(fname)

        print(f"\n  --- 생성 파일 확인 ---")
        for fname in expected_files:
            fpath = output_dir / fname
            exists = fpath.exists()
            size = fpath.stat().st_size if exists else 0
            status = f"OK ({size}B)" if exists else "MISSING"
            print(f"    {'v' if exists else 'x'} {fname} — {status}")

        if missing_files:
            _fail("3", elapsed, f"산출물 파일 누락: {', '.join(missing_files)}")
            return False

        # Validate each agent output in context
        print(f"\n  --- 에이전트별 검증 결과 ---")
        validation_errors = []
        agent_context_keys = {
            "대상분석": "대상_분석",
            "경쟁분석": "경쟁_분석",
            "플랫폼추천": "플랫폼_추천",
            "컨셉기획": "컨셉_기획",
        }
        for agent_name, ctx_key in agent_context_keys.items():
            output = context.get(ctx_key, "")
            if not output:
                validation_errors.append(f"{agent_name}: context 없음")
                print(f"    x {agent_name}: context 없음")
                continue
            val = OutputValidator.validate(agent_name, output, SUBJECT_NAME)
            t_agent = _agent_times.get(agent_name, 0)
            if val.passed:
                print(f"    v {agent_name}: PASS ({t_agent:.1f}s, {len(output)}자)")
            else:
                rules_str = "; ".join(val.failed_rules)
                validation_errors.append(f"{agent_name}: {rules_str}")
                print(f"    x {agent_name}: FAIL — {rules_str}")

        if validation_errors:
            _fail("3", elapsed, f"Validator 실패: {len(validation_errors)}개 에이전트")
            return False

        print(f"\n  총 소요 시간: {elapsed:.1f}s")
        _ok("3", elapsed, f"4개 에이전트 PASS, 산출물 {len(expected_files)}개 파일 생성")
        return True

    except Exception as e:
        elapsed = time.time() - t0
        _fail("3", elapsed, e)
        import traceback
        traceback.print_exc()
        return False


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "#" * 60)
    print("  인플루언서 에이전트 — Gemini E2E 테스트")
    print("  Provider: gemini  |  Model: gemini-2.0-flash")
    print("#" * 60)

    steps = [
        ("1", "API 연결", step1_api_connection),
        ("2", "대상분석 에이전트", step2_subject_analyst),
        ("3", "CEO E2E", step3_ceo_e2e),
    ]

    for step_no, step_name, step_fn in steps:
        passed = step_fn()
        if not passed:
            print(f"\n[STOP] Step {step_no} ({step_name}) 실패 — 이후 단계 중단")
            print("       위 에러 메시지 확인 후 수정 후 재실행\n")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("  ALL STEPS PASSED")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
