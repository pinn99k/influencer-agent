"""Unit + integration tests for ManagerAgent (V2 Spiral 5-D)."""
from unittest.mock import MagicMock

import pytest

from agents.manager import ManagerAgent


_CALENDAR = """### 4주 콘텐츠 캘린더
#### Week 1 (난이도: 입문)
1. **첫 시술 소개** — 쇼츠 / 인사
2. **도구 소개** — 쇼츠 / 준비물
3. **기본 팁** — 쇼츠 / 정보
#### Week 2 (난이도: 기초)
1. **비포애프터** — 쇼츠 / 변화
2. **고객 Q&A** — 쇼츠 / 소통
3. **트렌드 소개** — 쇼츠 / 정보
### 촬영 실행 가이드
- 장비: 스마트폰
"""


def _mgr(emitter=None):
    return ManagerAgent(MagicMock(), event_emitter=emitter)


class TestWeeklyCard:
    def test_weekly_card_basic(self):
        m = _mgr()
        card = m.generate_weekly_card(_CALENDAR, 1)
        assert "이번 주 할 일 (Week 1)" in card
        assert "첫 시술 소개" in card
        assert "업로드 체크리스트" in card

    def test_weekly_card_empty_calendar(self):
        m = _mgr()
        card = m.generate_weekly_card("", 2)
        assert "아직 생성되지 않았습니다" in card

    def test_weekly_card_invalid_week(self):
        m = _mgr()
        with pytest.raises(ValueError):
            m.generate_weekly_card(_CALENDAR, 0)
        with pytest.raises(ValueError):
            m.generate_weekly_card(_CALENDAR, 5)

    def test_file_save_path(self):
        m = _mgr()
        m.generate_weekly_card(_CALENDAR, 2)
        m._fm.save_manager_output.assert_called()
        fname = m._fm.save_manager_output.call_args[0][0]
        assert fname == "weekly_card_week2.md"


class TestProgressReport:
    def test_all_complete(self):
        m = _mgr()
        ar = {"대상_분석": "a", "경쟁_분석": "b", "플랫폼_추천": "c", "컨셉_기획": "d"}
        vr = {n: {"passed": True, "quality_score": 85} for n in
              ["대상분석", "경쟁분석", "플랫폼추천", "컨셉기획"]}
        rep = m.generate_progress_report(ar, vr)
        assert rep.count("완료 (품질 85/100)") == 4
        assert "대기중" not in rep

    def test_partial(self):
        m = _mgr()
        ar = {"대상_분석": "a", "경쟁_분석": "b"}
        vr = {"대상분석": {"passed": True, "quality_score": 80},
              "경쟁분석": {"passed": True, "quality_score": 75}}
        rep = m.generate_progress_report(ar, vr)
        assert rep.count("대기중") == 2


class TestOther:
    def test_performance_request_format(self):
        m = _mgr()
        msg = m.request_performance_input(2)
        assert "성과 기록 요청 (Week 2)" in msg
        assert "팔로워 수" in msg

    def test_completion_summary(self):
        m = _mgr()
        s = m.generate_completion_summary("## 최종\n- 1순위 플랫폼: 인스타그램")
        assert "지금 바로 할 3가지" in s
        assert "인스타그램" in s

    def test_notify_with_emitter(self):
        em = MagicMock()
        m = _mgr(emitter=em)
        m.notify("progress", "내용")
        em.emit.assert_called_once()
        assert em.emit.call_args[0][0] == "manager_notification"

    def test_notify_without_emitter(self):
        m = _mgr(emitter=None)
        m.notify("progress", "내용")  # 에러 없이 통과


class TestCEOIntegration:
    def test_ceo_has_manager(self):
        from agents.ceo import CEO
        ceo = CEO(MagicMock())
        assert hasattr(ceo, "_manager")

    def test_notify_manager_completion_calls_methods(self):
        from agents.ceo import CEO
        ceo = CEO(MagicMock())
        ceo._manager = MagicMock()
        ceo._notify_manager_completion({"컨셉_기획": _CALENDAR}, "최종 리포트")
        ceo._manager.generate_completion_summary.assert_called_once()
        ceo._manager.generate_weekly_card.assert_called_once()
        ceo._manager.request_performance_input.assert_called_once()
