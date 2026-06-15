import re
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    passed: bool
    agent_name: str
    failed_rules: list[str] = field(default_factory=list)
    retry_required: bool = False


class OutputValidator:
    """
    에이전트별 FORMAT 규칙 기반 자동 검증.
    키 = display_name (agent.display_name) 기준.
    """

    RULES = {
        "대상분석": {
            "required_sections": [
                "## 대상 분석 결과",
                "### 강점",
                "### 약점",
                "### 차별점",
            ],
            "required_keywords": ["**대상자:**", "근거:"],
            "count_checks": {"강점": 3, "약점": 3},
            "min_length": 300,
        },
        "경쟁분석": {
            "required_sections": [
                "## 경쟁 분석 결과",
                "### 유사 포지션 크리에이터",
                "### 시장 공백 기회",
                "### 차별 전략",
            ],
            "required_keywords": [
                "**대상자:**",
                "**데이터 출처:**",
                "**검색 키워드:**",
                "연결:",
            ],
            "count_checks": {"유사 포지션": 3},
            "min_length": 400,
        },
        "플랫폼추천": {
            "required_sections": [
                "## 플랫폼 추천 결과",
                "### 1순위 플랫폼",
                "### 2순위 플랫폼",
                "### 비추천 플랫폼",
            ],
            "required_keywords": ["**대상자:**", "출처:"],
            "min_length": 200,
        },
        "컨셉기획": {
            "required_sections": [
                "## 컨셉 기획 결과",
                "#### 컨셉 A:",
                "#### 컨셉 B:",
                "#### 컨셉 C:",
                "### 영상 아이디어",
                "### 4주 콘텐츠 캘린더",
                "### 영상 편집 컨셉",
                "### 촬영 실행 가이드",
                "### 업로드 최적화",
            ],
            "required_keywords": [
                "**대상자:**",
                "**성격 반영:**",
                "**차별점:**",
                "**공백 연결:**",
                "**추천 해시태그:**",
                "**캡션 템플릿:**",
            ],
            "count_checks": {"아이디어": 5},
            "min_length": 1200,
        },
    }

    # Generic phrases that are meaningless without specific follow-up
    GENERIC_PHRASES = [
        "다양한 정보",
        "꾸준한 업로드",
        "꾸준히",
        "다양한",
        "세부적인",
        "효과적으로",
        "적합하여",
        "전문적인 지식",
        "깊이 있는 분석",
        "깊이 있는",
        "높은 수준의",
        "큰 매력으로",
        "적극적으로 활용",
        "다양한 콘텐츠",
    ]

    @classmethod
    def _check_generic_phrases(cls, output: str) -> list[str]:
        """
        Detect 'solo generic phrases' — lines that contain a banned phrase
        but are too short or lack specifics (no digits, no proper nouns).
        Returns list of flagged lines (empty = pass).
        """
        flagged = []
        for line in output.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            for phrase in cls.GENERIC_PHRASES:
                if phrase in stripped:
                    # Solo heuristic: short line + no digits = generic
                    if len(stripped) < 40 and not re.search(r"\d", stripped):
                        flagged.append(stripped)
                        break  # one flag per line
        return flagged

    @classmethod
    def _check_incomplete_sentences(cls, output: str) -> list[str]:
        """Detect sentences that end mid-word or with particles."""
        VALID_ENDINGS = re.compile(
            r'(다|함|음|임|됨|있다|없다|한다|된다|이다|니다|습니다|이요|요|것|점|중)$'
            r'|[.!?)\]"]$'
        )
        # Lines with these patterns are label:value format, not prose
        LABEL_PATTERN = re.compile(r'^[-*]?\s*(출처|근거|연결|강점|약점|차별점|방향|공백)')
        lines = output.split("\n")
        content_lines = []
        incomplete = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Skip headers, bold labels, numbered sub-items, label:value lines
            if stripped.startswith("#") or stripped.startswith("**"):
                continue
            if ":" in stripped[:30] or LABEL_PATTERN.match(stripped):
                continue  # label:value format — not a sentence
            # Skip multi-step structured lines: "N. 설명 — 근거: xxx" — trailing label:value
            if "근거:" in stripped or "출처:" in stripped:
                continue
            # Skip video idea / calendar lines: "제목 — 포맷 / 설명" pattern
            if "—" in stripped and "/" in stripped:
                continue
            # Skip lines ending with label:value (e.g., "구독자: 미확인")
            if re.search(r'(구독자|조회수|팔로워):\s*\S+$', stripped):
                continue
            if stripped.startswith("- ") and len(stripped) > 40:
                content = stripped.rstrip()
                content_lines.append(content)
                if not VALID_ENDINGS.search(content):
                    incomplete.append(content[:60])
                continue
            if len(stripped) > 30:  # Only check substantial prose lines
                content_lines.append(stripped)
                if not VALID_ENDINGS.search(stripped.rstrip()):
                    incomplete.append(stripped[:60])
        return incomplete

    _NGRAM_WINDOW = 8
    _NGRAM_THRESHOLD = 10

    @classmethod
    def _check_repetitive_ngrams(cls, output: str) -> list[str]:
        """Detect repeated PHRASES (copy-paste / LLM degeneration).

        Uses an 8-char window, not 4: a 4-char window false-positives on legitimate
        domain vocabulary (e.g. a hairstylist's '스타일링' recurring 35x is normal,
        not copy-paste). Calibrated on real output: good domain text peaks ~4
        repeats at window 8, while degenerate copy-paste hits 12+. Threshold 10
        sits cleanly between."""
        w = cls._NGRAM_WINDOW
        text = re.sub(r'[#*\-\n\s]+', '', output)
        if len(text) < w * 2:
            return []
        ngrams = {}
        for i in range(len(text) - w + 1):
            gram = text[i:i + w]
            # Skip if all same char or pure ASCII (brand/term/URL names)
            if len(set(gram)) <= 1:
                continue
            if gram.isascii():
                continue
            ngrams[gram] = ngrams.get(gram, 0) + 1

        flagged = []
        for gram, count in ngrams.items():
            if count >= cls._NGRAM_THRESHOLD:
                flagged.append(f"'{gram}' x{count}")
        flagged.sort(key=lambda x: int(x.split('x')[-1]), reverse=True)
        return flagged[:5]  # Top 5

    @staticmethod
    def _extract_section(output: str, label: str) -> str:
        """label을 포함하는 첫 ### 섹션부터 다음 ### 섹션 전까지 추출."""
        lines = output.split("\n")
        capturing = False
        result = []
        for line in lines:
            if re.match(r"^#{2,4}\s+", line) and label in line:
                capturing = True
                continue
            if capturing and re.match(r"^#{2,4}\s+", line):
                break
            if capturing:
                result.append(line)
        return "\n".join(result)

    @classmethod
    def validate(cls, agent_name: str, output: str, subject_name: str) -> ValidationResult:
        """
        순서대로 체크:
        1. 필수 섹션 헤더 존재
        2. 대상자 이름 포함
        3. 필수 키워드 포함
        4. 개수 체크 (있는 경우)
        5. 최소 길이
        """
        rules = cls.RULES.get(agent_name, {})
        failed = []

        if not rules:
            return ValidationResult(passed=True, agent_name=agent_name)

        for section in rules.get("required_sections", []):
            if section not in output:
                failed.append(f"필수 섹션 누락: {section}")

        if subject_name not in output:
            failed.append(f"대상자 이름 누락: {subject_name}")

        for kw in rules.get("required_keywords", []):
            if kw not in output:
                failed.append(f"필수 키워드 누락: {kw}")

        for label, expected_count in rules.get("count_checks", {}).items():
            section_text = cls._extract_section(output, label)
            actual = len(re.findall(r"^\s*\d+\.", section_text, re.MULTILINE))
            if actual < expected_count:
                failed.append(f"개수 부족 [{label}]: {actual} < {expected_count}")

        min_len = rules.get("min_length", 0)
        if len(output) < min_len:
            failed.append(f"최소 길이 미달: {len(output)} < {min_len}")

        foreign_chars = re.findall(
            r"[一-鿿぀-ゟ゠-ヿ㐀-䶿À-ɏЀ-ӿ؀-ۿ฀-๿]", output
        )
        if foreign_chars:
            unique = set(foreign_chars)
            failed.append(f"외국어 문자 혼입 감지: {', '.join(unique)} ({len(foreign_chars)}개)")

        # 플레이스홀더 누출: 미수집 표시("정보 없음")가 사용자 산출물에 노출되면 실패.
        if agent_name == "컨셉기획" and "정보 없음" in output:
            failed.append("플레이스홀더 노출: '정보 없음'이 산출물에 그대로 출력됨")

        # Generic phrase detection (applies to all agents)
        generic_lines = cls._check_generic_phrases(output)
        if len(generic_lines) > 2:
            samples = generic_lines[:3]
            failed.append(
                f"generic_phrases: {len(generic_lines)}개 발견 — "
                + " / ".join(samples)
            )

        # Incomplete sentence check
        incomplete = cls._check_incomplete_sentences(output)
        if len(incomplete) > 0:
            total_lines = len([l for l in output.split("\n") if l.strip() and len(l.strip()) > 15])
            if total_lines > 0 and len(incomplete) / total_lines > 0.3:
                samples = incomplete[:3]
                failed.append(
                    f"불완전 문장 비율 초과: {len(incomplete)}/{total_lines} — "
                    + " / ".join(samples)
                )

        # Repetitive n-gram check
        rep_ngrams = cls._check_repetitive_ngrams(output)
        if rep_ngrams:
            failed.append(f"반복 표현 감지: {', '.join(rep_ngrams)}")

        # Special: competition analysis "미확인" saturation check
        if agent_name == "경쟁분석":
            unknown_count = output.count("미확인")
            if unknown_count >= 5:
                failed.append(f"'미확인' 과다 사용: {unknown_count}회 — Serper 데이터 활용 부족")

        passed = len(failed) == 0
        return ValidationResult(
            passed=passed,
            agent_name=agent_name,
            failed_rules=failed,
            retry_required=not passed,
        )
