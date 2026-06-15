"""Agent registry — single source of truth for agent order and metadata.

Adding an agent:
  1. Create BaseAgent subclass with all class vars set
  2. Add to AGENT_CLASSES below
  3. Add DEPENDENCIES entry below
  4. Add validation rules to OutputValidator.RULES
  5. Create prompt .md file
"""
from agents.subject_analyst import SubjectAnalystAgent
from agents.competition_analyst import CompetitionAnalystAgent
from agents.platform_recommender import PlatformRecommenderAgent
from agents.concept_planner import ConceptPlannerAgent

AGENT_CLASSES = [
    SubjectAnalystAgent,
    CompetitionAnalystAgent,
    PlatformRecommenderAgent,
    ConceptPlannerAgent,
]

# Dependency graph used by AgentScheduler.
# Key = agent display_name, value = list of display_names it must wait for.
# Wave 1: [대상분석]
# Wave 2: [경쟁분석, 플랫폼추천]  (parallel — both only need 대상분석)
# Wave 3: [컨셉기획]
DEPENDENCIES: dict[str, list[str]] = {
    "대상분석":  [],
    "경쟁분석":  ["대상분석"],
    "플랫폼추천": ["대상분석"],
    "컨셉기획":  ["경쟁분석", "플랫폼추천"],
}


def get_agent_order() -> list[str]:
    return [cls.display_name for cls in AGENT_CLASSES]


def get_context_keys() -> list[str]:
    return [cls.context_key for cls in AGENT_CLASSES]


def get_key_labels() -> list[tuple[str, str]]:
    """(context_key, output_label) pairs for final report."""
    return [(cls.context_key, cls.output_label) for cls in AGENT_CLASSES]
