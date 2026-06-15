import os
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

from core.config import LLM_MAX_RETRIES, LLM_TIMEOUT, LLM_TEMPERATURE, LLM_MAX_TOKENS
from core.llm_cache import get_cached, set_cached

CACHE_ENABLED = True

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── 상수 SSoT: 다른 파일에서 provider·model 상수 재정의 금지 ──
DEFAULT_PROVIDER = "groq"
DEFAULT_MODEL = "llama-3.3-70b-versatile"

# 503 overload 시 자동 전환 대상 (1회만, 무한 재귀 방지)
FALLBACK_MAP = {
    "gemini": ("groq", "llama-3.3-70b-versatile"),
    "openai": ("groq", "llama-3.3-70b-versatile"),
}

PROVIDER_CONFIG = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key_env": "GEMINI_API_KEY",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
}


def call_llm(
    provider: str,
    model: str,
    system: str,
    user: str,
    max_retries: int = LLM_MAX_RETRIES,
    max_tokens: int = LLM_MAX_TOKENS,
    _fallback: bool = False,
) -> str:
    """
    OpenAI 호환 엔드포인트 통일 호출.
    429 Rate Limit: Retry-After 헤더 또는 지수 백오프로 자동 재시도.
    503 Overload: max_retries 소진 후 FALLBACK_MAP 전환 (1회).
    그 외 에러: requests.HTTPError raise.
    """
    config = PROVIDER_CONFIG.get(provider)
    if config is None:
        raise ValueError(f"지원하지 않는 provider: {provider}. 가능: {list(PROVIDER_CONFIG)}")

    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        raise EnvironmentError(f"API 키 없음: {config['api_key_env']} (.env 확인)")

    url = f"{config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": LLM_TEMPERATURE,
        "max_tokens": max_tokens,
    }

    if CACHE_ENABLED:
        cached = get_cached(provider, model, system, user)
        if cached is not None:
            return cached

    last_resp = None
    last_status = None
    for attempt in range(max_retries + 1):
        last_resp = requests.post(url, headers=headers, json=payload, timeout=LLM_TIMEOUT)
        if last_resp.status_code in (429, 503):
            last_status = last_resp.status_code
            if attempt < max_retries:
                header_wait = last_resp.headers.get("Retry-After")
                if header_wait:
                    retry_after = min(int(header_wait), 60)
                else:
                    retry_after = min(15 * (attempt + 1), 60)
                tag = "rate limit" if last_resp.status_code == 429 else "server overload"
                print(f"[{tag}] {retry_after}초 후 재시도 ({attempt + 1}/{max_retries})...")
                time.sleep(retry_after)
                continue
            break  # max_retries 소진 — 루프 후 처리로
        last_resp.raise_for_status()
        result = last_resp.json()["choices"][0]["message"]["content"]
        if CACHE_ENABLED:
            set_cached(provider, model, system, user, result)
        return result

    # 429/503 max_retries 소진 + fallback 가능 + 첫 번째 시도 — 자동 전환
    if last_status in (429, 503) and not _fallback and provider in FALLBACK_MAP:
        fb_provider, fb_model = FALLBACK_MAP[provider]
        print(f"[fallback] {provider} 503 max_retries 소진 → {fb_provider}/{fb_model} 자동 전환")
        return call_llm(fb_provider, fb_model, system, user, max_retries, max_tokens, _fallback=True)

    last_resp.raise_for_status()


def call_llm_messages(
    provider: str,
    model: str,
    messages: list,
    max_retries: int = LLM_MAX_RETRIES,
    max_tokens: int = LLM_MAX_TOKENS,
    _fallback: bool = False,
) -> str:
    """멀티턴 대화용 호출 — messages 배열을 그대로 전달한다. 캐시 미사용.

    messages 예: [{"role": "system", ...}, {"role": "assistant", ...}, {"role": "user", ...}]
    429/503 재시도 + FALLBACK_MAP 전환은 call_llm과 동일.
    인터뷰처럼 턴마다 입력이 달라지는 경우에 사용한다.
    """
    config = PROVIDER_CONFIG.get(provider)
    if config is None:
        raise ValueError(f"지원하지 않는 provider: {provider}. 가능: {list(PROVIDER_CONFIG)}")

    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        raise EnvironmentError(f"API 키 없음: {config['api_key_env']} (.env 확인)")

    url = f"{config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": max_tokens,
    }

    last_resp = None
    last_status = None
    for attempt in range(max_retries + 1):
        last_resp = requests.post(url, headers=headers, json=payload, timeout=LLM_TIMEOUT)
        if last_resp.status_code in (429, 503):
            last_status = last_resp.status_code
            if attempt < max_retries:
                header_wait = last_resp.headers.get("Retry-After")
                if header_wait:
                    retry_after = min(int(header_wait), 60)
                else:
                    retry_after = min(15 * (attempt + 1), 60)
                tag = "rate limit" if last_resp.status_code == 429 else "server overload"
                print(f"[{tag}] {retry_after}초 후 재시도 ({attempt + 1}/{max_retries})...")
                time.sleep(retry_after)
                continue
            break
        last_resp.raise_for_status()
        return last_resp.json()["choices"][0]["message"]["content"]

    if last_status in (429, 503) and not _fallback and provider in FALLBACK_MAP:
        fb_provider, fb_model = FALLBACK_MAP[provider]
        print(f"[fallback] {provider} {last_status} max_retries 소진 -> {fb_provider}/{fb_model} 자동 전환")
        return call_llm_messages(fb_provider, fb_model, messages, max_retries, max_tokens, _fallback=True)

    last_resp.raise_for_status()
    raise RuntimeError("call_llm_messages: 응답 처리 실패")


def call_llm_tools(
    provider: str,
    model: str,
    messages: list,
    tools: list,
    tool_choice: str = "auto",
    max_retries: int = LLM_MAX_RETRIES,
    max_tokens: int = LLM_MAX_TOKENS,
    _fallback: bool = False,
) -> dict:
    """도구 호출 루프용 -- tools를 payload에 실어 assistant message(dict)를 반환한다.

    반환: API choices[0].message (content + tool_calls 포함). 호출측이 이 dict를
    messages에 그대로 append하고, tool_calls를 실행해 tool 결과를 다시 append한다.
    캐시 미사용(루프 상태 의존). 429/503 재시도 + FALLBACK_MAP 전환 동일.
    """
    config = PROVIDER_CONFIG.get(provider)
    if config is None:
        raise ValueError(f"지원하지 않는 provider: {provider}. 가능: {list(PROVIDER_CONFIG)}")

    api_key = os.getenv(config["api_key_env"])
    if not api_key:
        raise EnvironmentError(f"API 키 없음: {config['api_key_env']} (.env 확인)")

    url = f"{config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
        "max_tokens": max_tokens,
        "tools": tools,
        "tool_choice": tool_choice,
    }

    last_resp = None
    last_status = None
    for attempt in range(max_retries + 1):
        last_resp = requests.post(url, headers=headers, json=payload, timeout=LLM_TIMEOUT)
        if last_resp.status_code in (429, 503):
            last_status = last_resp.status_code
            if attempt < max_retries:
                header_wait = last_resp.headers.get("Retry-After")
                if header_wait:
                    retry_after = min(int(header_wait), 60)
                else:
                    retry_after = min(15 * (attempt + 1), 60)
                tag = "rate limit" if last_resp.status_code == 429 else "server overload"
                print(f"[{tag}] {retry_after}초 후 재시도 ({attempt + 1}/{max_retries})...")
                time.sleep(retry_after)
                continue
            break
        last_resp.raise_for_status()
        return last_resp.json()["choices"][0]["message"]

    if last_status in (429, 503) and not _fallback and provider in FALLBACK_MAP:
        fb_provider, fb_model = FALLBACK_MAP[provider]
        print(f"[fallback] {provider} {last_status} max_retries 소진 -> {fb_provider}/{fb_model} 전환")
        return call_llm_tools(fb_provider, fb_model, messages, tools, tool_choice,
                              max_retries, max_tokens, _fallback=True)

    last_resp.raise_for_status()
    raise RuntimeError("call_llm_tools: 응답 처리 실패")
