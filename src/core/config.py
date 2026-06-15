"""
Project-wide configuration — Single Source of Truth.

All paths are relative to src/ (runtime root).
All tuning constants live here. Do not re-define elsewhere.
"""
from pathlib import Path

# ── Directories (relative to src/) ──
BASE_DIR = Path(__file__).parent.parent          # src/
PROMPTS_DIR = BASE_DIR / "prompts"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
OUTPUTS_DIR = BASE_DIR / "outputs"

# ── Agent loop ──
MAX_RETRY = 1  # allow 1 retry for generic/quality failures
MAX_ITER_MULTIPLIER = 3         # max_iter = agent_count * this + 2

# ── LLM ──
LLM_MAX_RETRIES = 4             # 429 retry limit — Groq is stable, 4 is sufficient
LLM_TIMEOUT = 60                # seconds
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 8000           # full context pass-through requires more generation room (Gemini 1M ctx)
CEO_REPORT_MAX_TOKENS = 2500    # final strategy report needs more room than CEO judgment calls

# ── Web API (Spiral 3) ──
API_HOST = "127.0.0.1"
API_PORT = 8000
MAX_CONCURRENT_JOBS = 5
DECISION_TIMEOUT = 3600

# -- Quality judge (Spiral 2) --
QUALITY_THRESHOLD = 65
