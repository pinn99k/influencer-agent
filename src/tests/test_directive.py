"""Phase A — AgentDirective seam 테스트.

회귀 방지:
  - CEO plan의 per-agent 핵심 지시가 워커까지 도달한다 (고아 해소).
  - directive가 ceo_summary 키로 per-agent 주입된다 (없으면 일반 요약 폴백).
  - 사용자 방향이 구조화 주입되되, 채팅 append 방향은 verbatim 폴백한다.
"""
from unittest.mock import MagicMock, patch

from core.directive import AgentDirective
from core.direction import DirectionProfile
from agents.agent_context import build_context
from agents.ceo import CEO, AGENT_ORDER


# ── AgentDirective.to_prompt_text ────────────────────────────────

def test_directive_includes_strategy_instruction_feedback():
    d = AgentDirective(strategy="차별화 각도는 시술과정", instruction="20대 여성 타겟 채널만",
                       feedback="컨셉 B로")
    txt = d.to_prompt_text()
    assert "차별화 각도는 시술과정" in txt
    assert "20대 여성 타겟 채널만" in txt
    assert "컨셉 B로" in txt
    assert "[이 에이전트를 향한 핵심 지시]" in txt


def test_directive_structured_direction():
    md = DirectionProfile(content_focus="연습영상 위주").to_markdown("핑구")
    d = AgentDirective(strategy="s", direction_md=md)
    txt = d.to_prompt_text()
    assert "연습영상 위주" in txt
    assert "사용자가 정한 방향" in txt


def test_directive_chat_appended_direction_verbatim():
    # 채팅 포착 방향은 '- text' 불릿(섹션 없음) -> 구조화 파싱이 놓치므로 verbatim 폴백
    md = "# 방향\n- 프로필 꾸미기부터"
    d = AgentDirective(strategy="s", direction_md=md)
    txt = d.to_prompt_text()
    assert "프로필 꾸미기부터" in txt


def test_directive_blank_direction_omitted():
    blank = "# 방향\n\n## 콘텐츠 방향\n미정"
    d = AgentDirective(strategy="s", direction_md=blank)
    txt = d.to_prompt_text()
    assert "미정" not in txt


# ── _parse_agent_instructions ────────────────────────────────────

def test_parse_agent_instructions_from_plan_table():
    plan = (
        "# CEO 실행 계획\n"
        "## 에이전트 실행 계획\n"
        "| 순서 | 에이전트 | 핵심 지시 |\n"
        "|------|---------|-----------|\n"
        "| 1 | 대상분석 | 헤어컬러 강점 부각 |\n"
        "| 2 | 경쟁분석 | 20대 여성 타겟 채널 |\n"
    )
    out = CEO._parse_agent_instructions(plan)
    assert out.get("대상분석") == "헤어컬러 강점 부각"
    assert out.get("경쟁분석") == "20대 여성 타겟 채널"


# ── build_context per-agent directive 주입 ───────────────────────

def test_build_context_delivers_per_agent_directive():
    ctx = {"대상자": {"이름": "T"}, "ceo_summary": "일반요약",
           "directives": {"경쟁분석": "경쟁 전용 지시"}}
    out = build_context("경쟁분석", ctx)
    assert out["ceo_summary"] == "경쟁 전용 지시"


def test_build_context_falls_back_to_general_summary():
    ctx = {"대상자": {"이름": "T"}, "ceo_summary": "일반요약",
           "directives": {"경쟁분석": "경쟁 전용 지시"}}
    out = build_context("대상분석", ctx)   # 대상분석은 directive 없음 -> 일반
    assert out["ceo_summary"] == "일반요약"


# ── 통합: CEO 지시가 워커 directive까지 도달 ─────────────────────

def test_ceo_per_agent_instruction_reaches_worker():
    ceo = CEO(MagicMock(), dry_run=False)
    ctx = {"대상자": {"이름": "T", "목표": "g"},
           "에이전트_지시": {"경쟁분석": "X에 집중하라"}}
    with patch("agents.ceo.call_llm", return_value="전략 요약입니다"):
        ceo._build_ceo_summary(ctx)
    assert "X에 집중하라" in ctx["directives"]["경쟁분석"]
    assert "경쟁분석" in AGENT_ORDER
    out = build_context("경쟁분석", ctx)
    assert "X에 집중하라" in out["ceo_summary"]
