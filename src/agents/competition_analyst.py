import json
import re

from agents.base_agent import BaseAgent
from core import serper_client

# Korean number units (unicode-escaped to avoid CJK codepoint contamination):
#   억 = eok (10^8), 만 = man (10^4), 천 = cheon (10^3), 명 = myeong (counter)
_UNIT_EOK = "억"
_UNIT_MAN = "만"
_UNIT_CHEON = "천"
_UNIT_MYEONG = "명"


def _parse_subscriber_count(text):
    """Deterministically extract a subscriber count (int) from a snippet.

    Returns None when no count is found. Examples:
      '2.13만'   -> 21300      (2.13 man)
      '1.5K'         -> 1500
      '3M'           -> 3000000
      '12,300명' -> 12300      (myeong)
      '0.5억'    -> 50000000   (eok)
    Ordered by unit specificity; first match wins.
    """
    if not text:
        return None
    s = str(text)

    for unit, mult in ((_UNIT_EOK, 100_000_000), (_UNIT_MAN, 10_000), (_UNIT_CHEON, 1_000)):
        m = re.search(r"(\d+(?:\.\d+)?)\s*" + unit, s)
        if m:
            return int(float(m.group(1)) * mult)

    m = re.search(r"(\d+(?:\.\d+)?)\s*([KkMm])", s)
    if m:
        mult = 1_000 if m.group(2).lower() == "k" else 1_000_000
        return int(float(m.group(1)) * mult)

    # Plain number (>=2 digits, optional commas), optionally followed by the counter.
    m = re.search(r"(\d[\d,]+)\s*" + _UNIT_MYEONG + r"?", s)
    if m:
        digits = m.group(1).replace(",", "")
        if digits.isdigit():
            return int(digits)

    return None

_STEP1_EXTRACT = (
    "You are a data extraction specialist for YouTube/Instagram creator research.\n"
    "From the Serper search results below, extract ONLY real individual creators/channels.\n"
    "EXCLUDE: platforms (OKKY, GitHub, JobKorea), corporate accounts, news articles.\n\n"
    "For each real creator found, extract:\n"
    "- Channel/creator name (from title, remove ' - YouTube' suffix)\n"
    "- Subscriber count: if a result has a non-null '_subscriber_parsed' field, "
    "USE THAT EXACT NUMBER. Otherwise parse from snippet ('2.13만'=21300, '1.5K'=1500). "
    "If neither, write '[unknown]'.\n"
    "- Content focus/position description\n"
    "- Which search query found them\n\n"
    "Output in Korean. If fewer than 3 real creators found, note '[data insufficient]'.\n"
    "Format: numbered list with structured fields.\n"
)

_STEP2_POSITIONING = (
    "You are a market positioning analyst for the creator economy.\n"
    "Map the extracted creators on these axes:\n"
    "- Content depth: beginner/mass vs expert/deep\n"
    "- Tone: light/fun vs serious/informative\n"
    "- Format: shorts vs longform\n"
    "- Target age: teens-20s vs 30s+\n\n"
    "Then identify where the SUBJECT would fit on this map.\n"
    "Output in Korean. Be specific about each creator's position.\n"
)

_STEP3_GAP = (
    "You are a market gap analyst for creator positioning.\n"
    "Based on the positioning map, identify market gaps (empty spaces).\n"
    "Connect each gap to the subject's strengths from the subject analysis.\n"
    "Propose 1 differentiation strategy that links the gap to the subject's differentiator.\n\n"
    "Output in Korean. Every claim must cite data or analysis source.\n"
    "BANNED: 'consistent uploading', 'algorithm optimization' — only subject-specific strategies.\n"
)

_STEP4_FORMAT = (
    "You are assembling a competition analysis report in exact markdown format.\n"
    "Below are pre-analyzed data: extracted creators, positioning, gaps, and strategy.\n"
    "Assemble into this EXACT format. Do NOT change the analysis — only format it.\n"
    "Fix grammar. Ensure every sentence ends with proper Korean ending.\n\n"
    "Output ONLY Korean Hangul, English, and numbers. No CJK/Japanese/Cyrillic.\n\n"
    "## FORMAT:\n"
    "## 경쟁 분석 결과\n"
    "**대상자:** {name} ({job})\n"
    "**검색 키워드:** {queries used}\n"
    "**데이터 출처:** Serper 검색 결과\n\n"
    "### 유사 포지션 크리에이터\n"
    "1. **{name}** — {position description} / 구독자: {count}\n"
    "2. **{name}** — {position description} / 구독자: {count}\n"
    "3. **{name}** — {position description} / 구독자: {count}\n\n"
    "### 시장 공백 기회\n"
    "- {gap} — 근거: {data source} / 연결: {subject strength connection}\n\n"
    "### 차별 전략\n"
    "- {strategy} — 연결: 대상 분석 차별점 \"{differentiator quote}\"\n"
)


class CompetitionAnalystAgent(BaseAgent):
    display_name = "경쟁분석"
    prompt_file = "dept/planning/competition_analysis"
    knowledge_dir = "dept/planning/competition_analysis"
    context_key = "경쟁_분석"
    output_prefix = "02"
    output_label = "경쟁 분석"
    provider = "openai"
    model = "gpt-4o"

    def get_context_keys(self) -> list[str]:
        return ["대상자", "대상_분석"]

    def _build_search_queries(self, context: dict) -> list[str]:
        """크리에이터 중심 검색 쿼리 3개 생성.

        - 쿼리마다 '유튜버 OR 크리에이터 OR 채널' 접미어 추가
        - 목표 플랫폼(context에 있을 경우) 반영
        - 최대 3개로 제한
        """
        subject = context["대상자"]
        job = subject.get("직업", "")
        specialty = subject.get("특기", "")
        goal = subject.get("목표", "")
        target_age = subject.get("타겟연령대", "")

        creator_suffix = "유튜버 OR 크리에이터 OR 채널"

        # 플랫폼 힌트 — 목표 문자열에 플랫폼 키워드가 있으면 반영
        platform_hint = ""
        for kw in ["유튜브", "인스타", "틱톡"]:
            if kw in goal:
                platform_hint = kw
                break

        queries = []

        # Query 1: 직업 + 특기 + 크리에이터 접미어
        q1_parts = [p for p in [job, specialty] if p]
        if q1_parts:
            q1 = " ".join(q1_parts) + " " + creator_suffix
            if platform_hint:
                q1 = platform_hint + " " + q1
            queries.append(q1)

        # Query 2: 직업 + 타겟연령대 + 유튜브 채널 (연령대 타겟팅)
        if job and target_age:
            queries.append(f"{job} {target_age} 유튜브 채널")
        elif job:
            queries.append(f"{job} 유튜브 채널 추천")

        # Query 3: 특기 키워드 + 유튜버 (틈새 크리에이터 탐색)
        if specialty:
            queries.append(f"{specialty} 유튜버")

        # 중복 제거 + 최대 3개
        seen: set[str] = set()
        unique_queries: list[str] = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)
        return unique_queries[:3]

    def _collect_search_results(self, queries: list[str]) -> list[dict]:
        """Run each query once, dedupe by link, and attach a parsed subscriber count.

        Each result item gets:
          item["_query"]               -> the query that surfaced it
          item["_subscriber_parsed"]   -> int|None from snippet/title (deterministic)
        """
        seen_links: set[str] = set()
        all_results: list[dict] = []
        for q in queries:
            for item in serper_client.search(q):
                link = item.get("link", "")
                if link in seen_links:
                    continue
                seen_links.add(link)
                item["_query"] = q
                snippet = item.get("snippet", "") or ""
                title = item.get("title", "") or ""
                item["_subscriber_parsed"] = (
                    _parse_subscriber_count(snippet)
                    if _parse_subscriber_count(snippet) is not None
                    else _parse_subscriber_count(title)
                )
                all_results.append(item)
        return all_results

    def build_prompt(self, context: dict) -> str:
        """run()이 이미 수행한 검색 결과를 재사용한다.

        단독 호출(테스트·폴백)로 검색 결과가 컨텍스트에 없을 때만 직접 검색한다.
        이로써 run()->build_prompt 경로에서 검색이 두 번 실행되던 문제를 막는다.
        """
        if "serper_results" in context and "search_queries" in context:
            queries = context["search_queries"]
            all_results = context["serper_results"]
        else:
            queries = self._build_search_queries(context)
            all_results = self._collect_search_results(queries)

        payload = self._scoped_payload(context)
        payload["search_queries"] = queries
        payload["serper_results"] = all_results
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def run(self, context: dict) -> str:
        """Override to perform Serper search before multi-step execution."""
        queries = self._build_search_queries(context)
        all_results = self._collect_search_results(queries)
        # Inject search data into context for steps to use
        context["search_queries"] = queries
        context["serper_results"] = all_results
        # Now run multi-step (or single if get_steps is empty)
        steps = self.get_steps()
        if not steps:
            return self._single_call(context)
        return self._multi_step_call(context, steps)

    def get_steps(self) -> list[dict]:
        return []  # 단일 호출 모드 — multi-step은 Groq RPM 초과로 비활성화

    def _prompt_extract(self, context, step_results):
        subject = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        queries = context.get("search_queries", [])
        serper = json.dumps(context.get("serper_results", []), ensure_ascii=False, indent=2)
        return f"Subject:\n{subject}\n\nSearch queries: {queries}\n\nSerper results:\n{serper}"

    def _prompt_positioning(self, context, step_results):
        subject = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        subject_analysis = context.get("대상_분석", "")
        extracted = step_results.get("extract", "")
        return f"Subject:\n{subject}\n\nSubject analysis:\n{subject_analysis}\n\nExtracted creators:\n{extracted}"

    def _prompt_gap(self, context, step_results):
        subject_analysis = context.get("대상_분석", "")
        positioning = step_results.get("positioning", "")
        extracted = step_results.get("extract", "")
        return f"Subject analysis (with differentiator):\n{subject_analysis}\n\nPositioning map:\n{positioning}\n\nExtracted creators:\n{extracted}"

    def _prompt_format(self, context, step_results):
        subject = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        queries = context.get("search_queries", [])
        return (
            f"Subject:\n{subject}\n\n"
            f"Search queries used: {queries}\n\n"
            f"=== Extracted Creators ===\n{step_results.get('extract', '')}\n\n"
            f"=== Positioning Analysis ===\n{step_results.get('positioning', '')}\n\n"
            f"=== Gap & Strategy ===\n{step_results.get('gap', '')}\n\n"
            f"Assemble into the exact FORMAT specified in your system prompt."
        )
