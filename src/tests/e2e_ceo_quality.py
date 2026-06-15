"""Track-0 V-1/V-2: CEO supervisory-layer verification (real LLM).

WHY: CEO's LLM judgment methods are all wrapped in try/except and fall back
silently on failure. So "CEO.run() completed without error" proves NOTHING --
it could have run entirely on fallbacks. This script runs the FULL CEO.run()
with real LLM and INSTRUMENTS each judgment to detect whether it actually fired
(real LLM output) or fell back.

Scope correction (verified in code, session 28):
  CEO.run() -> _agent_loop -> PlanningDepartment.run().  CEO's own _decide_next
  and _judge_quality are NOT on the live path (dead code, tests only). The CEO
  judgments that ACTUALLY fire are:
    - _interpret_goal        (L159) -> plan.md
    - _build_ceo_summary     (L289) -> ceo_summary for sub-agents
    - _handle_agent_questions(L329) -> 3-way question routing
    - _check_briefing_for_chairman (only if dept briefing exists)
  Plus PlanningDepartment's own LLM calls (worker runs, _judge_quality, compress,
  briefing) and ManagerAgent (template, no LLM).

Writes (in src/):
  _e2e_ceo_summary.txt   -> fallback counts + validity scores (safe to read)
  _e2e_ceo_full.txt      -> plan.md, ceo_summary, manager outputs

Run from src/:  python tests/e2e_ceo_quality.py
Requires OPENAI_API_KEY (+ SERPER_API_KEY) in src/.env
"""
import os
import io
import sys
import traceback
from pathlib import Path

# Windows: force UTF-8 stdout like main.py/api.main do (this is a TEST HARNESS;
# production entry points already wrap stdout, so this is not a product fix).
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace", line_buffering=True)
    except (AttributeError, ValueError):
        pass

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
os.chdir(SRC_DIR)

import core.llm_client as llm_mod
from core.file_manager import FileManager
from agents.ceo import CEO

SUBJECT = {
    "이름": "박지훈",
    "직업": "미용사",
    "특기": "남성 컷 전문, 빠른 스타일링, 두피 케어 상담",
    "성격": "활발하고 말하기를 즐김, 카메라 앞에서 편안함",
    "타겟연령대": "20-40대 남성",
    "SNS경험": "유튜브 시청만 함, 직접 올린 적 없음",
    "목표": "1개월 내 유튜브 쇼츠로 구독자 500명",
    "가용시간": "주 3회, 회당 1시간 가능 (휴무일 활용)",
}

# ---- fallback instrumentation -------------------------------------------------
# We wrap call_llm / call_llm_messages so we can count total calls and detect
# raised exceptions (which would trigger CEO's silent fallbacks).
_stats = {"call_llm": 0, "call_llm_messages": 0, "exceptions": 0, "errors": []}
_real_call_llm = llm_mod.call_llm
_real_call_msgs = getattr(llm_mod, "call_llm_messages", None)


def _wrapped_call_llm(*a, **k):
    _stats["call_llm"] += 1
    try:
        return _real_call_llm(*a, **k)
    except Exception as e:  # noqa
        _stats["exceptions"] += 1
        _stats["errors"].append(f"call_llm: {type(e).__name__}: {e}")
        raise


def _wrapped_call_msgs(*a, **k):
    _stats["call_llm_messages"] += 1
    try:
        return _real_call_msgs(*a, **k)
    except Exception as e:  # noqa
        _stats["exceptions"] += 1
        _stats["errors"].append(f"call_llm_messages: {type(e).__name__}: {e}")
        raise


def main():
    # Patch at module level + in ceo module namespace (it imported call_llm by name)
    llm_mod.call_llm = _wrapped_call_llm
    if _real_call_msgs:
        llm_mod.call_llm_messages = _wrapped_call_msgs
    import agents.ceo as ceo_mod
    ceo_mod.call_llm = _wrapped_call_llm
    import departments.planning as plan_mod
    plan_mod.call_llm = _wrapped_call_llm

    context = {"대상자": SUBJECT}
    fm = FileManager(SUBJECT["이름"])
    ceo = CEO(fm, dry_run=False)

    summary = []
    full = ["# CEO E2E (real LLM) — Track 0 V-1/V-2\n"]
    run_error = None
    try:
        ceo.run(context)
    except Exception as e:  # noqa
        run_error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"

    # ---- fallback detection (the core V-1 result) ----
    # Inspect the live-path judgment outputs for fallback signatures.
    plan = context.get("_plan_text")  # not stored; read from file instead
    plan_path = fm.base / ".system" / "ceo" / "plan.md"
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    progress_path = fm.base / ".system" / "ceo" / "progress.md"
    progress_text = progress_path.read_text(encoding="utf-8") if progress_path.exists() else ""
    ceo_summary = context.get("ceo_summary", "")
    qresp = context.get("질문_응답", {})

    # Fallback signatures (from code):
    #  _interpret_goal fallback -> plan contains "[LLM call failed:"
    #  _build_ceo_summary fallback -> ceo_summary == "" (empty)
    #  _handle_agent_questions fallback -> all questions escalated (or no questions)
    plan_fellback = "[LLM call failed" in plan_text
    summary_fellback = (ceo_summary.strip() == "")

    summary.append(f"run_error: {run_error if run_error else 'NONE'}")
    summary.append(f"total call_llm: {_stats['call_llm']}")
    summary.append(f"total call_llm_messages: {_stats['call_llm_messages']}")
    summary.append(f"llm exceptions (fallback triggers): {_stats['exceptions']}")
    summary.append(f"_interpret_goal fallback: {plan_fellback}")
    summary.append(f"_build_ceo_summary fallback (empty): {summary_fellback}")
    summary.append(f"ceo_summary length: {len(ceo_summary)}")
    summary.append(f"question routing: answers={len(qresp.get('answers', {}))} "
                   f"escalated={len(qresp.get('escalated', []))} "
                   f"data_requests={len(qresp.get('data_requests', []))}")
    # Worker outputs present?
    wk = {k: bool(context.get(k)) for k in
          ["대상_분석", "경쟁_분석", "플랫폼_추천", "컨셉_기획"]}
    summary.append(f"worker outputs present: {wk}")
    # Manager outputs (V-3 quick check)
    mgr_dir = fm.base / ".system" / "manager"
    mgr_files = sorted(p.name for p in mgr_dir.glob("*.md")) if mgr_dir.exists() else []
    summary.append(f"manager outputs: {mgr_files}")
    if _stats["errors"]:
        summary.append("errors: " + " | ".join(_stats["errors"][:5]))

    # Strategy-preservation check: plan.md must keep the LLM strategy,
    # progress checklist must live in progress.md.
    plan_has_strategy = ("전략 방향" in plan_text) or ("초기 가설" in plan_text)
    plan_is_just_checklist = ("남은 에이전트" in plan_text) and not plan_has_strategy
    summary.append(f"plan.md preserves strategy: {plan_has_strategy}")
    summary.append(f"plan.md is bare checklist (BUG if True): {plan_is_just_checklist}")
    summary.append(f"progress.md exists: {bool(progress_text)}")

    full.append("\n## plan.md\n" + plan_text)
    full.append("\n## progress.md\n" + progress_text)
    full.append("\n## ceo_summary\n" + ceo_summary)
    full.append("\n## question routing\n" + str(qresp))
    for mf in mgr_files:
        full.append(f"\n## manager/{mf}\n" + (mgr_dir / mf).read_text(encoding="utf-8"))

    with open("_e2e_ceo_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(summary) + "\n")
    with open("_e2e_ceo_full.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(full))

    print("DONE")
    for line in summary:
        print(line)


if __name__ == "__main__":
    main()
