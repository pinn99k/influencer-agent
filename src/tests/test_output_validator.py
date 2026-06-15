import pytest

from validators.output_validator import OutputValidator, ValidationResult


SUBJECT_NAME = '테스트크리에이터'

# ── RULES 키 (모듈 로드 시 한 번만 계산) ────────────────────────────────────
_K_대상   = next(k for k in OutputValidator.RULES if "대상" in k)
_K_경쟁   = next(k for k in OutputValidator.RULES if "경쟁" in k)
_K_플랫폼 = next(k for k in OutputValidator.RULES if "플랫폼" in k)
_K_컨셉   = next(k for k in OutputValidator.RULES if "컨셉" in k)


# ── 유효 픽스처 (repr 리터럴 — codepoint 일치 보장) ─────────────────────────

_VALID_대상 = '## 대상 분석 결과\n**대상자:** 테스트크리에이터\n\n### 강점\n1. 강점1\n   근거: 직업 미용사\n2. 강점2\n   근거: 특기 헤어컬러\n3. 강점3\n   근거: 섬세한 성격\n\n### 약점\n1. 약점1\n   근거: 내향적 성격\n2. 약점2\n   근거: SNS 경험 부족\n3. 약점3\n   근거: 팔로워 200명\n\n### 차별점\n- 헤어컬러 전문 미용사 관점\n  근거: 차별점 근거\n## 대상 분석 결과\n**대상자:** 테스트크리에이터\n\n### 강점\n1. 강점1\n   근거: 직업 미용사\n2. 강점2\n   근거: 특기 헤어컬러\n3. 강점3\n   근거: 섬세한 성격\n\n### 약점\n1. 약점1\n   근거: 내향적 성격\n2. 약점2\n   근거: SNS 경험 부족\n3. 약점3\n   근거: 팔로워 200명\n\n### 차별점\n- 헤어컬러 전문 미용사 관점\n  근거: 차별점 근거\n'

_VALID_경쟁 = '## 경쟁 분석 결과\n**대상자:** 테스트크리에이터\n**검색 키워드:** 미용사 헤어컬러 유튜버\n**데이터 출처:** Serper 검색 결과 | 추론 기반\n\n### 유사 포지션 크리에이터\n1. 유사 포지션 크리에이터 A\n   - 콘텐츠 유형: 헤어\n   - 추정 구독자 규모: 5만\n   - 강점: 전문성\n   - 약점: 단조로움\n2. 유사 포지션 크리에이터 B\n   - 콘텐츠 유형: 뷰티\n   - 추정 구독자 규모: 3만\n   - 강점: 친근함\n   - 약점: 깊이 부족\n3. 유사 포지션 크리에이터 C\n   - 콘텐츠 유형: 살롱\n   - 추정 구독자 규모: 2만\n   - 강점: 현장감\n   - 약점: 편집 품질\n\n### 시장 공백 기회\n- 공백1: 연결: 헤어컬러 전문 지식으로 채울 수 있음\n- 공백2: 연결: 내향적 섬세함으로 차별화 가능\n\n### 차별 전략\n- 테스트크리에이터을 위한 포지셔닝 전략\n  근거: 공백과 강점 연결\n## 경쟁 분석 결과\n**대상자:** 테스트크리에이터\n**검색 키워드:** 미용사 헤어컬러 유튜버\n**데이터 출처:** Serper 검색 결과 | 추론 기반\n\n### 유사 포지션 크리에이터\n1. 유사 포지션 크리에이터 A\n   - 콘텐츠 유형: 헤어\n   - 추정 구독자 규모: 5만\n   - 강점: 전문성\n   - 약점: 단조로움\n2. 유사 포지션 크리에이터 B\n   - 콘텐츠 유형: 뷰티\n   - 추정 구독자 규모: 3만\n   - 강점: 친근함\n   - 약점: 깊이 부족\n3. 유사 포지션 크리에이터 C\n   - 콘텐츠 유형: 살롱\n   - 추정 구독자 규모: 2만\n   - 강점: 현장감\n   - 약점: 편집 품질\n\n### 시장 공백 기회\n- 공백1: 연결: 헤어컬러 전문 지식으로 채울 수 있음\n- 공백2: 연결: 내향적 섬세함으로 차별화 가능\n\n### 차별 전략\n- 테스트크리에이터을 위한 포지셔닝 전략\n  근거: 공백과 강점 연결\n'

_VALID_플랫폼 = '## 플랫폼 추천 결과\n**대상자:** 테스트크리에이터\n\n### 1순위 플랫폼\n**플랫폼:** 유튜브\n**추천 이유:** 헤어컬러 튜토리얼은 긴 영상 포맷이 적합\n**핵심 근거:**\n- 특기(헤어컬러)와 유튜브 튜토리얼 포맷 일치\n출처: 대상자 특기 + 경쟁 시장 공백\n\n### 2순위 플랫폼\n**플랫폼:** 인스타그램\n**추천 이유:** 비포&애프터 이미지 콘텐츠 적합\n출처: 대상자 SNS경험 참조\n\n### 비추천 플랫폼\n**플랫폼:** 틱톡\n**비추천 이유:** 내향적 성격과 짧은 포맷 부적합\n## 플랫폼 추천 결과\n**대상자:** 테스트크리에이터\n\n### 1순위 플랫폼\n**플랫폼:** 유튜브\n**추천 이유:** 헤어컬러 튜토리얼은 긴 영상 포맷이 적합\n**핵심 근거:**\n- 특기(헤어컬러)와 유튜브 튜토리얼 포맷 일치\n출처: 대상자 특기 + 경쟁 시장 공백\n\n### 2순위 플랫폼\n**플랫폼:** 인스타그램\n**추천 이유:** 비포&애프터 이미지 콘텐츠 적합\n출처: 대상자 SNS경험 참조\n\n### 비추천 플랫폼\n**플랫폼:** 틱톡\n**비추천 이유:** 내향적 성격과 짧은 포맷 부적합\n'

_VALID_컨셉 = '## 컨셉 기획 결과\n**대상자:** 테스트크리에이터\n\n### 컨셉 옵션\n\n#### 컨셉 A: 헤어컬러 비밀\n**성격 반영:** 내향적 섬세함\n**차별점:** 미용사 시점\n**공백 연결:** 헤어케어 공백\n\n#### 컨셉 B: 살롱 일상\n**성격 반영:** 섬세함\n**차별점:** 리얼 살롱 현장\n**공백 연결:** 현장감 공백\n\n#### 컨셉 C: 홈케어 가이드\n**성격 반영:** 차분한 설명\n**차별점:** 전문가 홈케어\n**공백 연결:** 홈케어 공백\n\n### 영상 아이디어\n1. 제목1 상세 설명 텍스트임\n2. 제목2 상세 설명 텍스트임\n3. 제목3 상세 설명 텍스트임\n4. 제목4 상세 설명 텍스트임\n5. 제목5 상세 설명 텍스트임\n\n### 4주 콘텐츠 캘린더\n#### Week 1\n1. **첫 인사 영상** — 쇼츠 / 채널 소개와 방향 제시\n2. **헤어컬러 기초** — 쇼츠 / 염색 전 기본 상식 전달\n\n#### Week 2\n1. **블리치 과정 공개** — 쇼츠 / 실제 시술 과정 공개\n2. **고객 비포애프터** — 쇼츠 / 시술 전후 비교 공개\n\n#### Week 3\n1. **홈케어 추천템** — 쇼츠 / 염색 후 관리법 소개\n2. **살롱 하루 일과** — 쇼츠 / 미용사의 하루 공개\n\n#### Week 4\n1. **실패 케이스 공개** — 쇼츠 / 시술 실수 수습 과정\n2. **한 달 정리** — 쇼츠 / 첫 한 달 성과 정리\n\n### 영상 편집 컨셉\n- **훅(첫 3초):** 질문형 훅으로 시청자의 궁금증을 유발한다\n- **전개 구조:** 0-3초 훅, 3-10초 문제 제시, 10-25초 과정, 25-30초 결과와 CTA로 구성한다\n- **자막 스타일:** 하단 중앙에 핵심 키워드를 강조하여 음소거 시청에 대응한다\n- **컷·전환·BGM:** 빠른 컷과 부드러운 전환, 잔잔한 배경음을 사용한다\n\n### 촬영 실행 가이드\n- **촬영 장비:** 스마트폰 기본 촬영이며 삼각대만 추가 사용함\n- **촬영 팁:** 살롱 조명을 활용하고 손동작 위주로 촬영함\n- **편집 팁:** CapCut 무료 앱으로 자막과 배경음을 추가함\n- **성격 기반 포맷:** 내향적이므로 손만 나오는 시술 위주임\n\n### 업로드 최적화\n- **추천 해시태그:** #헤어컬러 #미용사일상 #살롱시술 #염색전후 #블리치 #헤어케어팁 #컬러체인지 #머리염색 #살롱추천 #헤어트렌드\n- **캡션 템플릿:** 오늘의 시술 기록이다\n- **업로드 추천 시간대:** 평일 저녁 7시에서 9시 사이가 적합함\n\n### 추가 전략 노트\n컨셉 A는 헤어컬러에 관심 있는 20대 여성을 주요 타겟으로 설정한다. 블리치 과정의 투명한 공개가 핵심 차별 요소이다. 컨셉 B는 미용사 지망생이나 현직 미용사를 보조 타겟으로 삼는다. 살롱 현장의 리얼한 일상을 공유하여 공감대를 형성한다. 컨셉 C는 모든 연령대의 일반 소비자를 대상으로 전문가 수준의 홈케어 정보를 제공한다. 세 컨셉 모두 대상자의 긍정적 성격과 좋은 목소리를 활용하여 편안한 분위기의 콘텐츠를 지향한다.\n'


# ── 섹션 헤더 리터럴 (replace 테스트용) ──────────────────────────────────────
_SEC_대상_강점    = '### 강점'
_SEC_경쟁_공백   = '### 시장 공백 기회'
_SEC_플랫폼_비추천 = '### 비추천 플랫폼'
_SEC_컨셉_A      = '#### 컨셉 A:'


class TestValidate대상분析:
    def test_pass_with_valid_output(self):
        result = OutputValidator.validate(_K_대상, _VALID_대상, SUBJECT_NAME)
        assert result.passed is True
        assert result.retry_required is False
        assert result.failed_rules == []

    def test_fail_missing_required_section(self):
        output = _VALID_대상.replace(_SEC_대상_강점, "### 장점")
        result = OutputValidator.validate(_K_대상, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("강점" in r for r in result.failed_rules)

    def test_fail_missing_subject_name(self):
        output = _VALID_대상.replace(SUBJECT_NAME, "다른이름")
        result = OutputValidator.validate(_K_대상, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("대상자 이름 누락" in r for r in result.failed_rules)

    def test_fail_missing_required_keyword(self):
        output = _VALID_대상.replace("근거:", "이유:")
        result = OutputValidator.validate(_K_대상, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("근거:" in r for r in result.failed_rules)

    def test_fail_too_short(self):
        rules = OutputValidator.RULES[_K_대상]
        short = (
            rules["required_sections"][0] + "\n"
            + f"**대상자:** {SUBJECT_NAME}\n"
            + rules["required_sections"][1] + "\n1. a\n근거: b\n2. c\n근거: d\n3. e\n근거: f\n"
            + rules["required_sections"][2] + "\n1. g\n근거: h\n2. i\n근거: j\n3. k\n근거: l\n"
            + rules["required_sections"][3] + "\n- m\n근거: n\n"
        ).format(SUBJECT_NAME=SUBJECT_NAME)
        result = OutputValidator.validate(_K_대상, short, SUBJECT_NAME)
        assert result.passed is False
        assert any("최소 길이 미달" in r for r in result.failed_rules)

    def test_retry_required_on_failure(self):
        result = OutputValidator.validate(_K_대상, "짧은 내용", SUBJECT_NAME)
        assert result.retry_required is True

    def test_result_is_validation_result_type(self):
        result = OutputValidator.validate(_K_대상, _VALID_대상, SUBJECT_NAME)
        assert isinstance(result, ValidationResult)
        assert result.agent_name == _K_대상


class TestValidate경쟁분析:
    def test_pass_with_valid_output(self):
        result = OutputValidator.validate(_K_경쟁, _VALID_경쟁, SUBJECT_NAME)
        assert result.passed is True
        assert result.failed_rules == []

    def test_fail_missing_required_section(self):
        output = _VALID_경쟁.replace(_SEC_경쟁_공백, "### 공백 기회")
        result = OutputValidator.validate(_K_경쟁, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("시장 공백 기회" in r for r in result.failed_rules)

    def test_fail_missing_data_source_keyword(self):
        output = _VALID_경쟁.replace("**데이터 출처:**", "**출처:**")
        result = OutputValidator.validate(_K_경쟁, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("데이터 출처" in r for r in result.failed_rules)

    def test_fail_missing_link_keyword(self):
        output = _VALID_경쟁.replace("연결:", "관련:")
        result = OutputValidator.validate(_K_경쟁, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("연결:" in r for r in result.failed_rules)

    def test_fail_missing_subject_name(self):
        output = _VALID_경쟁.replace(SUBJECT_NAME, "다른이름")
        result = OutputValidator.validate(_K_경쟁, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("대상자 이름 누락" in r for r in result.failed_rules)

    def test_fail_too_short(self):
        rules = OutputValidator.RULES[_K_경쟁]
        short = (
            rules["required_sections"][0] + "\n"
            + f"**대상자:** {SUBJECT_NAME}\n"
            + "**검색 키워드:** test\n"
            + "**데이터 출처:** 추론 기반\n"
            + rules["required_sections"][1] + "\n1. A\n2. B\n3. C\n"
            + rules["required_sections"][2] + "\n- 공백: 연결: 연결\n"
            + rules["required_sections"][3] + "\n- 전략\n"
        ).format(SUBJECT_NAME=SUBJECT_NAME)
        result = OutputValidator.validate(_K_경쟁, short, SUBJECT_NAME)
        assert result.passed is False
        assert any("최소 길이 미달" in r for r in result.failed_rules)


class TestValidate플랫폼추천:
    def test_pass_with_valid_output(self):
        result = OutputValidator.validate(_K_플랫폼, _VALID_플랫폼, SUBJECT_NAME)
        assert result.passed is True
        assert result.failed_rules == []

    def test_fail_missing_required_section(self):
        output = _VALID_플랫폼.replace(_SEC_플랫폼_비추천, "### 추천안함")
        result = OutputValidator.validate(_K_플랫폼, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("비추천 플랫폼" in r for r in result.failed_rules)

    def test_fail_missing_source_keyword(self):
        output = _VALID_플랫폼.replace("출처:", "참조:")
        result = OutputValidator.validate(_K_플랫폼, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("출처:" in r for r in result.failed_rules)

    def test_fail_missing_subject_name(self):
        output = _VALID_플랫폼.replace(SUBJECT_NAME, "다른이름")
        result = OutputValidator.validate(_K_플랫폼, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("대상자 이름 누락" in r for r in result.failed_rules)

    def test_fail_too_short(self):
        rules = OutputValidator.RULES[_K_플랫폼]
        short = (
            rules["required_sections"][0] + "\n"
            + f"**대상자:** {SUBJECT_NAME}\n"
            + rules["required_sections"][1] + "\n**플랫폼:** 유튜브\n출처: 참조\n"
            + rules["required_sections"][2] + "\n**플랫폼:** 인스타그램\n출처: 참조\n"
            + rules["required_sections"][3] + "\n**플랫폼:** 틱톡\n"
        ).format(SUBJECT_NAME=SUBJECT_NAME)
        result = OutputValidator.validate(_K_플랫폼, short, SUBJECT_NAME)
        assert result.passed is False
        assert any("최소 길이 미달" in r for r in result.failed_rules)


class TestValidate컨셉기획:
    def test_pass_with_valid_output(self):
        result = OutputValidator.validate(_K_컨셉, _VALID_컨셉, SUBJECT_NAME)
        assert result.passed is True

    def test_fail_missing_concept_section(self):
        output = _VALID_컨셉.replace(_SEC_컨셉_A + " 헤어컬러 비밀", "#### 개념 A: 헤어컬러 비밀")
        result = OutputValidator.validate(_K_컨셉, output, SUBJECT_NAME)
        assert result.passed is False


class TestValidateCJKDetection:
    def test_fail_on_cjk_characters(self):
        output = _VALID_대상.replace("직업 미용사", "직업 미용사 经验丰富")
        result = OutputValidator.validate(_K_대상, output, SUBJECT_NAME)
        assert result.passed is False
        assert any("외국어 문자" in r for r in result.failed_rules)

    def test_pass_without_cjk(self):
        result = OutputValidator.validate(_K_대상, _VALID_대상, SUBJECT_NAME)
        assert result.passed is True
        assert not any("외국어 문자" in r for r in result.failed_rules)


class TestValidateUnknownAgent:
    def test_unknown_agent_passes_with_any_output(self):
        result = OutputValidator.validate("없는에이전트", "아무 내용", "아무이름")
        assert result.passed is True


class TestRepetitiveNgrams:
    """Seam bug (E2E dry-run): a legitimate 4-char domain word recurring (e.g. a
    hairstylist's '스타일링' x35) used to false-positive as copy-paste. Window
    raised 4->8 so only repeated phrases flag."""

    def test_domain_word_repetition_not_flagged(self):
        # '스타일링' recurs in DIFFERENT contexts (like real domain output) -> no
        # repeated 8-char phrase, so it must not be flagged.
        pre = ("남성 여성 두피 컬러 펌 트렌드 여름 겨울 데일리 파티 웨딩 면접 데이트 "
               "학생 직장 운동 캠핑 여행 복고 청량 시크 모던 내추럴 단정").split()
        post = ("입문 기초 심화 응용 실전 비법 노하우 가이드 추천 정리 분석 리뷰 비교 "
                "정석 꿀팁 후기 모음 총정리 핵심 요약 입장 변신 마스터 정복").split()
        text = ". ".join(f"{a} 스타일링 {b}" for a, b in zip(pre, post)) + "."
        assert text.count("스타일링") >= 20
        assert OutputValidator._check_repetitive_ngrams(text) == []

    def test_copy_paste_phrase_is_flagged(self):
        text = "이 채널은 전문적인 스타일을 제공합니다. " * 12  # repeated phrase
        assert OutputValidator._check_repetitive_ngrams(text) != []

    def test_clean_text_not_flagged(self):
        assert OutputValidator._check_repetitive_ngrams("짧은 정상 문장입니다.") == []


class TestPlaceholderLeak:
    """컨셉기획 산출물에 미수집 표시('정보 없음')가 사용자 화면에 노출되면 FAIL.
    실사용자(예으니) 산출물에서 발견된 결함을 못 박는 회귀 테스트."""

    def test_concept_with_placeholder_flagged(self):
        leaked = _VALID_컨셉.replace("**성격 반영:** 내향적 섬세함",
                                     "**성격 반영:** 정보 없음")
        assert "정보 없음" in leaked
        result = OutputValidator.validate(_K_컨셉, leaked, SUBJECT_NAME)
        assert result.passed is False
        assert any("플레이스홀더" in r for r in result.failed_rules)

    def test_concept_without_placeholder_passes(self):
        result = OutputValidator.validate(_K_컨셉, _VALID_컨셉, SUBJECT_NAME)
        assert not any("플레이스홀더" in r for r in result.failed_rules)

    def test_placeholder_scoped_to_concept_only(self):
        leaked = _VALID_대상.replace("섬세한 성격", "정보 없음")
        result = OutputValidator.validate(_K_대상, leaked, SUBJECT_NAME)
        assert not any("플레이스홀더" in r for r in result.failed_rules)
