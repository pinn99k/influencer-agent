from unittest.mock import MagicMock, patch

from agents.ceo import CEO


def _ceo():
    fm = MagicMock()
    return CEO(fm, dry_run=False)


def _context():
    return {
        "대상자": {"이름": "테스터"},
        "대상_분석": "대상 분석",
        "경쟁_분석": "경쟁 분석",
        "플랫폼_추천": "플랫폼 추천",
        "컨셉_기획": "컨셉 기획",
    }


def test_synthesize_final_report_uses_llm_when_sections_present():
    text = (
        "# 테스터 인플루언서 전략 보고서\n\n"
        "## 한 줄 결론\n결론\n\n"
        "## 핵심 결정 3가지\n1. 플랫폼: A - B\n\n"
        "## 강점과 기회\n강점\n\n"
        "## 4주 실행 로드맵\n- Week 1: 실행\n\n"
        "## 지금 당장 할 3가지\n1. 실행\n\n"
        "## 성공 지표 (30일)\n- 팔로워: 300\n\n"
        "## 매주 반복 루틴\n1. 찍기\n\n"
        "## 성과 기록 (매주 1줄)\n- 팔로워 기록\n\n"
        "## 2주 후 셀프 점검\n- 잘된 것 더\n"
    )

    with patch("agents.ceo.call_llm", return_value=text) as mock_call:
        result = _ceo()._synthesize_final_report(_context())

    assert result == text.strip()
    assert mock_call.called


def test_synthesize_final_report_falls_back_when_sections_missing():
    ceo = _ceo()
    ceo._reports.build_final_report = MagicMock(return_value="fallback report")

    with patch("agents.ceo.call_llm", return_value="missing sections"):
        result = ceo._synthesize_final_report(_context())

    assert result == "fallback report"
    ceo._reports.build_final_report.assert_called_once()
