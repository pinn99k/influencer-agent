from core.config import PROMPTS_DIR, KNOWLEDGE_DIR


KNOWLEDGE_MAP = {
    "전략수립": ["management/01_strategic", "management/02_marketing", "management/06_operations"],
    "품질판단": ["management/05_quality", "management/08_decision"],
    "보고판단": ["management/07_risk", "management/09_communication"],
    "ROI판단":  ["management/03_finance", "management/04_organization"],
}


class PromptLoader:
    """CEO/agent prompt and knowledge file loading.
    SRP: file reading only - no judgment or saving."""

    @staticmethod
    def load_prompt(name: str) -> str:
        path = PROMPTS_DIR / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"CEO prompt file not found: {path}")
        return path.read_text(encoding="utf-8")

    @staticmethod
    def load_knowledge_for(judgment_type: str) -> str:
        dirs = KNOWLEDGE_MAP.get(judgment_type, [])
        parts = []
        for d in dirs:
            path = KNOWLEDGE_DIR / d
            if path.exists():
                parts += [p.read_text(encoding="utf-8") for p in sorted(path.glob("*.md"))]
        return "\n\n---\n\n".join(parts)
