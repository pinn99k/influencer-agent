import re
from abc import ABC, abstractmethod

from core.llm_client import call_llm, DEFAULT_PROVIDER, DEFAULT_MODEL  # SSoT import
from core.config import PROMPTS_DIR, KNOWLEDGE_DIR, LLM_MAX_TOKENS

# Foreign characters to strip from LLM output:
# CJK ideographs, Japanese Hiragana/Katakana, accented Latin (é, ü, ñ etc.),
# Cyrillic, Arabic, Thai, and other non-Korean/non-English scripts
def _strip_think_block(text: str) -> str:
    """Remove <think>...</think> blocks from LLM output.
    Also handles bare 'think\\n...\\n' blocks without angle brackets."""
    # Tagged form: <think>...</think>
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Bare form: starts with 'think\n' (some models omit angle brackets)
    if text.lstrip().startswith("think\n"):
        # Find end of think block — look for double newline or FORMAT header
        lines = text.split("\n")
        start = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("## ") or line.strip().startswith("# ["):
                start = i
                break
        if start > 0:
            text = "\n".join(lines[start:])
    return text.strip()


_FOREIGN_CHAR_RE = re.compile(
    r"[一-鿿぀-ゟ゠-ヿ㐀-䶿"       # CJK + Japanese
    r"À-ɏ"                  # Latin Extended (accented: é, ü, ñ, etc.)
    r"Ѐ-ӿ"                  # Cyrillic
    r"؀-ۿ"                  # Arabic
    r"฀-๿"                  # Thai
    r"]"
)


class BaseAgent(ABC):
    display_name: str = ""   # 한글 표시명 (state.md 출력용)
    prompt_file: str = ""    # prompts/ 하위 경로 (확장자 제외) — "dept/planning/subject_analysis"
    knowledge_dir: str = ""  # knowledge/ 하위 경로 — "" 이면 지식 없음
    context_key: str = ""    # context dict 저장 키 — "대상_분석" 등
    output_prefix: str = "00"  # 산출물 파일 번호 — "01", "02" 등
    output_label: str = ""     # 최종 리포트 표시명 — "대상 분석" 등
    provider: str = ""       # empty = use DEFAULT_PROVIDER
    model: str = ""          # empty = use DEFAULT_MODEL

    def __init__(self):
        self.system_prompt = self._load_template() + self._load_knowledge()

    def run(self, context: dict) -> str:
        steps = self.get_steps()
        if not steps:
            return self._single_call(context)
        return self._multi_step_call(context, steps)

    def get_steps(self) -> list[dict]:
        """Override to define multi-step execution.

        Each step dict: {"name": str, "system": str, "prompt_builder": callable, "max_tokens": int}
        prompt_builder signature: (context: dict, step_results: dict[str, str]) -> str
        Empty list = single call (backward compatible).
        """
        return []

    def _single_call(self, context: dict) -> str:
        """Original single LLM call."""
        user_prompt = self.build_prompt(context)
        p = self.provider or DEFAULT_PROVIDER
        m = self.model or DEFAULT_MODEL
        result = call_llm(p, m, self.system_prompt, user_prompt)
        result = _strip_think_block(result)
        return _FOREIGN_CHAR_RE.sub("", result)

    def _multi_step_call(self, context: dict, steps: list[dict]) -> str:
        """Execute steps sequentially. Each step result feeds into the next."""
        p = self.provider or DEFAULT_PROVIDER
        m = self.model or DEFAULT_MODEL
        step_results: dict[str, str] = {}
        knowledge_text = self._load_knowledge()

        for step in steps:
            system = step["system"]
            if knowledge_text:
                system = system + "\n\n# DOMAIN KNOWLEDGE\n" + knowledge_text

            user_prompt = step["prompt_builder"](context, step_results)
            max_tok = step.get("max_tokens", LLM_MAX_TOKENS)
            result = call_llm(p, m, system, user_prompt, max_tokens=max_tok)
            result = _strip_think_block(result)
            result = _FOREIGN_CHAR_RE.sub("", result)
            step_results[step["name"]] = result

        return step_results[steps[-1]["name"]]

    @abstractmethod
    def build_prompt(self, context: dict) -> str:
        """에이전트별 user_prompt 조합. 각 에이전트가 구현."""
        ...

    @abstractmethod
    def get_context_keys(self) -> list[str]:
        """이 에이전트에 필요한 context 키 목록."""
        ...

    def _scoped_payload(self, context: dict) -> dict:
        """Base prompt payload: this agent's scoped context keys plus the CEO
        strategic directive (ceo_summary) when present.

        ceo_summary carries the reanalysis feedback verbatim, so including it
        here is what lets re-run agents actually act on the user's correction.
        Absent ceo_summary (e.g. first analysis without it) -> unchanged payload.
        """
        payload = {k: context[k] for k in self.get_context_keys() if k in context}
        directive = (context.get("ceo_summary") or "").strip()
        if directive:
            payload["ceo_전략_지시"] = directive
        return payload

    def _load_template(self) -> str:
        path = PROMPTS_DIR / f"{self.prompt_file}.md"
        if not path.exists():
            raise FileNotFoundError(f"프롬프트 파일 없음: {path}")
        return path.read_text(encoding="utf-8")

    def _load_knowledge(self) -> str:
        """
        knowledge/{knowledge_dir}/ 하위 .md 전부 읽어 병합.
        knowledge_dir = "" 이면 빈 문자열 반환.
        하위 폴더 포함 재귀 로딩(rglob). 경로 알파벳순 정렬 → 순서 보장.
        """
        if not self.knowledge_dir:
            return ""
        base = KNOWLEDGE_DIR / self.knowledge_dir
        if not base.exists():
            return ""
        parts = [p.read_text(encoding="utf-8") for p in sorted(base.rglob("*.md"))]
        if not parts:
            return ""
        return "\n\n---\n\n" + "\n\n---\n\n".join(parts)
