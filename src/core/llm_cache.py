import hashlib
import json
from datetime import datetime
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "llm"


def _make_key(provider: str, model: str, system: str, user: str) -> str:
    raw = f"{provider}|{model}|{system}|{user}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def get_cached(provider: str, model: str, system: str, user: str) -> "str | None":
    key = _make_key(provider, model, system, user)
    cache_file = CACHE_DIR / f"{key}.json"
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        return data["response"]
    except Exception:
        return None


def set_cached(provider: str, model: str, system: str, user: str, response: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = _make_key(provider, model, system, user)
    system_hash = hashlib.md5(system.encode("utf-8")).hexdigest()
    user_hash = hashlib.md5(user.encode("utf-8")).hexdigest()
    data = {
        "provider": provider,
        "model": model,
        "system_hash": system_hash,
        "user_hash": user_hash,
        "response": response,
        "cached_at": datetime.now().isoformat(),
    }
    cache_file = CACHE_DIR / f"{key}.json"
    cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_cache() -> None:
    if not CACHE_DIR.exists():
        return
    for f in CACHE_DIR.glob("*.json"):
        f.unlink()
