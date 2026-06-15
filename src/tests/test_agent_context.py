"""Unit tests for AgentContext.build_context (V2 Spiral 5-A)."""
from agents.agent_context import AGENT_SCOPES, build_context


def _full():
    return {
        "대상자": {"이름": "테스트"},
        "ceo_summary": "전략 요약",
        "대상_분석": "분석 결과",
        "경쟁_분석": "경쟁 결과",
        "검증_결과": {},
    }


class TestBuildContext:
    def test_subject_analyst_reads_subject_and_summary(self):
        # 대상분석도 ceo_summary 를 받는다 — 재분석 피드백이 ceo_summary 로 전달되는 경로
        ctx = build_context("대상분석", _full())
        assert set(ctx.keys()) == {"대상자", "ceo_summary"}

    def test_competition_analyst_reads_subject_and_summary(self):
        # B1: also receives 대상_분석 via outputs mapping (01_대상분석.md)
        ctx = build_context("경쟁분석", _full())
        assert set(ctx.keys()) == {"대상자", "ceo_summary", "대상_분석"}

    def test_ceo_reads_everything(self):
        full = _full()
        ctx = build_context("CEO", full)
        assert set(ctx.keys()) == set(full.keys())

    def test_unknown_agent_returns_full_copy(self):
        full = _full()
        ctx = build_context("미등록에이전트", full)
        assert set(ctx.keys()) == set(full.keys())
        assert ctx is not full  # copy, not same reference

    def test_missing_key_silently_skipped(self):
        partial = {"대상자": {"이름": "테스트"}}  # no ceo_summary
        ctx = build_context("경쟁분석", partial)
        assert set(ctx.keys()) == {"대상자"}

    def test_returns_copy_not_reference(self):
        full = _full()
        ctx = build_context("CEO", full)
        assert ctx is not full


class TestAgentScopes:
    def test_all_planning_agents_present(self):
        for name in ["CEO", "대상분석", "경쟁분석", "플랫폼추천", "컨셉기획"]:
            assert name in AGENT_SCOPES

    def test_every_scope_has_read_key(self):
        for name, scope in AGENT_SCOPES.items():
            assert "read" in scope
            assert isinstance(scope["read"], list)


class TestOutputMapping:
    def _full_with_outputs(self):
        return {
            "대상자": {"이름": "테스트"},
            "ceo_summary": "전략 요약",
            "대상_분석": "대상 결과",
            "경쟁_분석": "경쟁 결과",
            "플랫폼_추천": "플랫폼 결과",
        }

    def test_subject_excludes_outputs(self):
        ctx = build_context("대상분석", self._full_with_outputs())
        # outputs=[] -> 이전 산출물 제외. ceo_summary 는 read 스코프라 포함.
        assert set(ctx.keys()) == {"대상자", "ceo_summary"}
        for k in ["대상_분석", "경쟁_분석", "플랫폼_추천"]:
            assert k not in ctx

    def test_competition_includes_only_subject_output(self):
        ctx = build_context("경쟁분석", self._full_with_outputs())
        assert "대상_분석" in ctx
        assert "경쟁_분석" not in ctx
        assert "플랫폼_추천" not in ctx

    def test_platform_includes_subject_and_competition(self):
        ctx = build_context("플랫폼추천", self._full_with_outputs())
        assert "대상_분석" in ctx
        assert "경쟁_분석" in ctx
        assert "플랫폼_추천" not in ctx

    def test_concept_includes_all_three_priors(self):
        ctx = build_context("컨셉기획", self._full_with_outputs())
        for k in ["대상_분석", "경쟁_분석", "플랫폼_추천"]:
            assert k in ctx

    def test_missing_prior_output_skipped(self):
        partial = {"대상자": {"이름": "테스트"}}  # no 대상_분석 yet
        ctx = build_context("경쟁분석", partial)
        assert "대상_분석" not in ctx
        assert set(ctx.keys()) == {"대상자"}
