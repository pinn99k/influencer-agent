"""Tests for extended foreign char detection and generic phrase detection."""
import pytest
from validators.output_validator import OutputValidator


SUBJECT_NAME = "TestCreator"

# Use the existing RULES keys
_K_SUBJ = next(k for k in OutputValidator.RULES if k.startswith("대상"))
_K_COMP = next(k for k in OutputValidator.RULES if k.startswith("경쟁"))


def _make_valid_subject_output() -> str:
    """Build a minimal valid subject analysis output that passes structural checks."""
    block = (
        "## 대상 분석 결과\n"
        "**대상자:** TestCreator\n\n"
        "### 강점\n"
        "1. 강점 one detail here with number 10 -- 콘텐츠 형식: specific format -- 근거: field1, field2\n"
        "2. 강점 two detail here with 20 units -- 콘텐츠 형식: another format -- 근거: field3, field4\n"
        "3. 강점 three detail here with 30 -- 콘텐츠 형식: third format -- 근거: field5, field6\n\n"
        "### 약점\n"
        "1. 약점 one -- 근거: field1, field2\n"
        "2. 약점 two -- 근거: field3, field4\n"
        "3. 약점 three -- 근거: field5, field6\n\n"
        "### 차별점\n"
        "- 차별점 description here\n  근거: field1, field2\n"
    )
    return block * 2  # repeat to exceed min_length of 300


class TestForeignCharDetection:
    """Extended foreign character detection: accented Latin, Cyrillic, etc."""

    def test_detect_accented_latin_e_acute(self):
        output = _make_valid_subject_output().replace("one detail", "vidéos detail")
        result = OutputValidator.validate(_K_SUBJ, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("외국어 문자" in r for r in result.failed_rules)

    def test_detect_accented_latin_u_umlaut(self):
        output = _make_valid_subject_output().replace("one detail", "Brücke detail")
        result = OutputValidator.validate(_K_SUBJ, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("외국어 문자" in r for r in result.failed_rules)

    def test_detect_cyrillic(self):
        output = _make_valid_subject_output().replace("two detail", "контент detail")
        result = OutputValidator.validate(_K_SUBJ, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("외국어 문자" in r for r in result.failed_rules)

    def test_detect_cjk_still_works(self):
        output = _make_valid_subject_output().replace("one detail", "经验丰富 detail")
        result = OutputValidator.validate(_K_SUBJ, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("외국어 문자" in r for r in result.failed_rules)

    def test_detect_japanese_katakana(self):
        output = _make_valid_subject_output().replace("one detail", "リアル detail")
        result = OutputValidator.validate(_K_SUBJ, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("외국어 문자" in r for r in result.failed_rules)

    def test_clean_korean_english_no_foreign_flag(self):
        output = _make_valid_subject_output()
        result = OutputValidator.validate(_K_SUBJ, output, SUBJECT_NAME)
        assert not any("외국어 문자" in r for r in result.failed_rules)


class TestGenericPhraseDetection:
    """Generic phrase detection added in harness engineering."""

    def test_no_flag_with_clean_output(self):
        output = _make_valid_subject_output()
        result = OutputValidator.validate(_K_SUBJ, output, SUBJECT_NAME)
        assert not any("generic_phrases" in r for r in result.failed_rules)

    def test_flag_many_generic_short_lines(self):
        # >2 short generic lines should trigger failure
        generic_lines = "\n꾸준히\n다양한\n세부적인\n효과적으로\n"
        output = _make_valid_subject_output() + generic_lines
        result = OutputValidator.validate(_K_SUBJ, output, SUBJECT_NAME)
        assert any("generic_phrases" in r for r in result.failed_rules)

    def test_no_flag_when_generic_in_long_line_with_digit(self):
        # Generic phrase in a long line (>40 chars) with digits should NOT flag
        long_line = (
            "블리치 시술 과정의 다양한 "
            "단계를 15분 분량의 롱폼 영상으로 "
            "제작하여 20대 여성에게 전달한다"
        )
        output = _make_valid_subject_output() + "\n" + long_line + "\n"
        result = OutputValidator.validate(_K_SUBJ, output, SUBJECT_NAME)
        assert not any("generic_phrases" in r for r in result.failed_rules)

    def test_threshold_is_more_than_two(self):
        # Exactly 2 generic short lines should NOT trigger (threshold is >2)
        generic_lines = "\n꾸준히\n다양한\n"
        output = _make_valid_subject_output() + generic_lines
        result = OutputValidator.validate(_K_SUBJ, output, SUBJECT_NAME)
        assert not any("generic_phrases" in r for r in result.failed_rules)
