import json

from agents.base_agent import BaseAgent

# Step system prompts — English for encoding safety, Korean output instruction
_STEP1_STRENGTHS = (
    "You are an influencer marketing specialist with 10 years of experience.\n"
    "Your ONLY task: analyze the subject's 3 strengths for content creation.\n"
    "Each strength MUST name a specific content format (e.g., 'before/after hair color shorts').\n"
    "Each strength MUST cite which input field it comes from.\n\n"
    "Output in Korean. Every sentence must end properly (다/함/음/임/됨).\n"
    "BANNED: '전문적인 지식', '다양한 콘텐츠', '높은 수준의' — be specific.\n"
    "Format: numbered list, 3 items only.\n"
    "1. {strength} — content format: {specific format} — source: {field name}\n"
)

_STEP2_WEAKNESSES = (
    "You are an influencer marketing specialist with 10 years of experience.\n"
    "Your ONLY task: analyze the subject's 3 weaknesses for content creation.\n"
    "Each weakness MUST include a concrete overcome direction.\n"
    "Consider the strengths already identified (provided below) to avoid contradiction.\n\n"
    "Output in Korean. Every sentence must end properly.\n"
    "BANNED: generic advice like 'work hard', 'be consistent'.\n"
    "Format: numbered list, 3 items only.\n"
    "1. {weakness} — overcome: {specific method} — source: {field name}\n"
)

_STEP3_DIFFERENTIATOR = (
    "You are an influencer marketing specialist with 10 years of experience.\n"
    "Your ONLY task: identify 1 differentiator by crossing 2+ strengths.\n"
    "The differentiator must be something competitors cannot easily replicate.\n"
    "Use the strengths and weaknesses provided below.\n\n"
    "Output in Korean. One paragraph, max 3 sentences.\n"
    "Format: {job/specialty} + {personality trait} creator provides {what} to {target}.\n"
    "Cite which input fields support this differentiator.\n"
)

_STEP4_ASSEMBLE = (
    "You are an influencer marketing specialist assembling a final analysis report.\n"
    "Below are pre-analyzed strengths, weaknesses, and differentiator.\n"
    "Your task: assemble them into the exact markdown FORMAT below.\n"
    "Do NOT change the analysis — only format it correctly.\n"
    "Fix any grammar issues. Ensure every sentence ends with proper Korean ending.\n"
    "Remove any generic phrases. Verify all placeholders are filled.\n\n"
    "Output ONLY Korean Hangul, English, and numbers.\n"
    "No CJK/Hanja, no Japanese, no Cyrillic.\n\n"
    "## FORMAT:\n"
    "## 대상 분석 결과\n"
    "**대상자:** {name} ({job})\n\n"
    "### 강점\n"
    "1. {s1} — 콘텐츠 형식: {format} — 근거: {fields}\n"
    "2. {s2} — 콘텐츠 형식: {format} — 근거: {fields}\n"
    "3. {s3} — 콘텐츠 형식: {format} — 근거: {fields}\n\n"
    "### 약점\n"
    "1. {w1} — 극복 방향: {method} — 근거: {fields}\n"
    "2. {w2} — 극복 방향: {method} — 근거: {fields}\n"
    "3. {w3} — 극복 방향: {method} — 근거: {fields}\n\n"
    "### 차별점\n"
    "- {differentiator sentence} — 근거: {fields}\n"
)


class SubjectAnalystAgent(BaseAgent):
    display_name = "대상분석"
    prompt_file = "dept/planning/subject_analysis"
    knowledge_dir = "dept/planning/subject_analysis"
    context_key = "대상_분석"
    output_prefix = "01"
    output_label = "대상 분석"
    provider = "openai"
    model = "gpt-4o"

    def get_context_keys(self) -> list[str]:
        return ["대상자"]

    def build_prompt(self, context: dict) -> str:
        payload = self._scoped_payload(context)
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def get_steps(self) -> list[dict]:
        return []  # 단일 호출 모드 — multi-step은 Groq RPM 초과로 비활성화

    def _prompt_strengths(self, context: dict, step_results: dict) -> str:
        subject = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        return f"Subject information:\n{subject}\n\nAnalyze 3 strengths for content creation."

    def _prompt_weaknesses(self, context: dict, step_results: dict) -> str:
        subject = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        strengths = step_results.get("strengths", "")
        return (
            f"Subject information:\n{subject}\n\n"
            f"Already identified strengths:\n{strengths}\n\n"
            f"Now analyze 3 weaknesses. Do not contradict the strengths above."
        )

    def _prompt_differentiator(self, context: dict, step_results: dict) -> str:
        subject = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        strengths = step_results.get("strengths", "")
        weaknesses = step_results.get("weaknesses", "")
        return (
            f"Subject information:\n{subject}\n\n"
            f"Strengths:\n{strengths}\n\n"
            f"Weaknesses:\n{weaknesses}\n\n"
            f"Find the differentiator by crossing 2+ strengths."
        )

    def _prompt_assemble(self, context: dict, step_results: dict) -> str:
        subject = json.dumps(context["대상자"], ensure_ascii=False, indent=2)
        return (
            f"Subject information:\n{subject}\n\n"
            f"=== Pre-analyzed Strengths ===\n{step_results.get('strengths', '')}\n\n"
            f"=== Pre-analyzed Weaknesses ===\n{step_results.get('weaknesses', '')}\n\n"
            f"=== Pre-analyzed Differentiator ===\n{step_results.get('differentiator', '')}\n\n"
            f"Assemble into the exact FORMAT specified in your system prompt."
        )
