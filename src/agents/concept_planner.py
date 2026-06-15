import json

from agents.base_agent import BaseAgent

_STEP1_CONCEPTS = (
    "You are an SNS content strategy director.\n"
    "Your ONLY task: create 3 distinct channel concepts for this creator.\n"
    "Use the differentiator x target matrix and competition gaps.\n"
    "The 3 concepts MUST differ on at least 2 axes: tone, format, depth.\n\n"
    "Output in Korean. Be specific — no generic concepts like 'daily vlog'.\n"
    "For each concept: name, direction (1 line), differentiator, gap connection.\n"
)

_STEP2_IDEAS = (
    "You are an SNS content strategy director.\n"
    "Your ONLY task: create 5 video ideas based on Concept A from the concepts below.\n"
    "Each idea MUST have a title that could be an actual YouTube/Instagram post title.\n"
    "Specify format: shorts/longform/live. Add a 1-line description.\n\n"
    "Output in Korean. BANNED: 'beauty tips collection', 'daily vlog' — be specific.\n"
    "Only ideas the creator can execute alone with a smartphone.\n"
)

_STEP3_CALENDAR = (
    "You are an SNS content calendar planner.\n"
    "Your ONLY task: create a 4-week content calendar based on the video ideas below.\n"
    "Rules:\n"
    "- Week 1-4, each week 2-3 items\n"
    "- NO duplicate titles across weeks\n"
    "- Start with easier content in Week 1, gradually increase complexity\n"
    "- Each item: title + format (shorts/longform) + core message (1 line)\n"
    "- Default duration: 30 seconds or less (creator works 8-10 hours/day)\n\n"
    "Output in Korean. Every title must be unique.\n"
)

_STEP4_GUIDE = (
    "You are a practical content creation coach.\n"
    "Your ONLY task: create a filming guide and upload optimization tips.\n"
    "Filming guide:\n"
    "- Equipment: smartphone default, minimize extras\n"
    "- Tips: lighting, angles, using workplace as set\n"
    "- Editing: recommend beginner-friendly FREE apps (CapCut, InShot, VLLO)\n"
    "  Do NOT recommend DaVinci Resolve or Adobe Premiere (too complex for beginners)\n"
    "- Personality-based format: if introverted, hands-only/no-face first\n\n"
    "Upload optimization:\n"
    "- 10 specific hashtags for the creator's niche (NO generic like #daily #vlog)\n"
    "- 1 caption template reflecting creator's specialty\n"
    "- Recommended posting time with reasoning\n\n"
    "Output in Korean.\n"
)

_STEP5_ASSEMBLE = (
    "You are assembling a complete concept planning report in exact markdown format.\n"
    "Below are pre-created: concepts, video ideas, calendar, and guide.\n"
    "Assemble into the EXACT format below. Fix grammar, ensure complete sentences.\n"
    "Verify NO duplicate titles in the calendar. Remove any generic phrases.\n\n"
    "Output ONLY Korean Hangul, English, and numbers. No CJK/Japanese/Cyrillic.\n\n"
    "## FORMAT:\n"
    "## 컨셉 기획 결과\n"
    "**대상자:** {name} ({job})\n"
    "**기준 플랫폼:** {1st choice platform}\n"
    "**성격 반영:** {personality} → {how reflected}\n\n"
    "### 채널 컨셉\n"
    "#### 컨셉 A: {name}\n- **방향:** ...\n- **차별점:** ...\n- **공백 연결:** ...\n\n"
    "#### 컨셉 B: {name}\n- **방향:** ...\n- **차별점:** ...\n- **공백 연결:** ...\n\n"
    "#### 컨셉 C: {name}\n- **방향:** ...\n- **차별점:** ...\n- **공백 연결:** ...\n\n"
    "### 영상 아이디어 (컨셉 A 기준)\n"
    "1. **{title}** — format / description\n...\n\n"
    "### 4주 콘텐츠 캘린더\n"
    "#### Week 1\n1. ...\n2. ...\n"
    "#### Week 2\n...\n"
    "#### Week 3\n...\n"
    "#### Week 4\n...\n\n"
    "### 촬영 실행 가이드\n"
    "- **촬영 장비:** ...\n- **촬영 팁:** ...\n- **편집 팁:** ...\n- **성격 기반 포맷:** ...\n\n"
    "### 업로드 최적화\n"
    "- **추천 해시태그:** {10 specific hashtags}\n"
    "- **캡션 템플릿:** ...\n"
    "- **업로드 추천 시간대:** ...\n"
)


class ConceptPlannerAgent(BaseAgent):
    display_name = "컨셉기획"
    prompt_file = "dept/planning/concept_planning"
    knowledge_dir = "dept/planning/concept_planning"
    context_key = "컨셉_기획"
    output_prefix = "04"
    output_label = "컨셉 기획"
    provider = "openai"
    model = "gpt-4o"

    def get_context_keys(self) -> list[str]:
        return ["대상자", "대상_분석", "경쟁_분석", "플랫폼_추천"]

    def build_prompt(self, context: dict) -> str:
        payload = self._scoped_payload(context)
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def get_steps(self) -> list[dict]:
        return []  # 단일 호출 모드 — multi-step은 Groq RPM 초과로 비활성화

    def _prompt_concepts(self, context, step_results):
        subject = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        subject_analysis = context.get("대상_분석", "")
        competition = context.get("경쟁_분석", "")
        platform = context.get("플랫폼_추천", "")
        return (
            f"Subject:\n{subject}\n\n"
            f"Subject analysis:\n{subject_analysis}\n\n"
            f"Competition analysis:\n{competition}\n\n"
            f"Platform recommendation:\n{platform}\n\n"
            f"Create 3 distinct channel concepts."
        )

    def _prompt_ideas(self, context, step_results):
        subject = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        concepts = step_results.get("concepts", "")
        platform = context.get("플랫폼_추천", "")
        return (
            f"Subject:\n{subject}\n\n"
            f"Concepts (use Concept A):\n{concepts}\n\n"
            f"Platform recommendation:\n{platform}\n\n"
            f"Create 5 video ideas for Concept A."
        )

    def _prompt_calendar(self, context, step_results):
        subject = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        ideas = step_results.get("ideas", "")
        concepts = step_results.get("concepts", "")
        return (
            f"Subject:\n{subject}\n\n"
            f"Concepts:\n{concepts}\n\n"
            f"Video ideas:\n{ideas}\n\n"
            f"Create a 4-week calendar. NO duplicate titles."
        )

    def _prompt_guide(self, context, step_results):
        subject = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        platform = context.get("플랫폼_추천", "")
        return (
            f"Subject:\n{subject}\n\n"
            f"Platform:\n{platform}\n\n"
            f"Create filming guide and upload optimization."
        )

    def _prompt_assemble(self, context, step_results):
        subject = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        return (
            f"Subject:\n{subject}\n\n"
            f"=== Concepts ===\n{step_results.get('concepts', '')}\n\n"
            f"=== Video Ideas ===\n{step_results.get('ideas', '')}\n\n"
            f"=== Calendar ===\n{step_results.get('calendar', '')}\n\n"
            f"=== Guide & Optimization ===\n{step_results.get('guide', '')}\n\n"
            f"Assemble into the exact FORMAT in your system prompt. Verify NO duplicate calendar titles."
        )
