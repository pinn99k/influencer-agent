import json

from agents.base_agent import BaseAgent


class PlatformRecommenderAgent(BaseAgent):
    display_name = "플랫폼추천"
    prompt_file = "dept/planning/platform_recommendation"
    knowledge_dir = "dept/planning/platform_recommendation"
    context_key = "플랫폼_추천"
    output_prefix = "03"
    output_label = "플랫폼 추천"
    provider = "openai"
    model = "gpt-4o"

    def get_context_keys(self) -> list[str]:
        return ["대상자", "대상_분석", "경쟁_분석"]

    def build_prompt(self, context: dict) -> str:
        payload = self._scoped_payload(context)
        return json.dumps(payload, ensure_ascii=False, indent=2)
