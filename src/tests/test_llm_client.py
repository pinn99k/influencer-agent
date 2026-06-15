import pytest
from unittest.mock import patch, MagicMock

from core.llm_client import (
    call_llm,
    DEFAULT_PROVIDER,
    DEFAULT_MODEL,
    PROVIDER_CONFIG,
    FALLBACK_MAP,
)

# DEFAULT_PROVIDER의 api_key_env — 환경 변수 mock에 사용
_DEFAULT_API_KEY_ENV = PROVIDER_CONFIG[DEFAULT_PROVIDER]["api_key_env"]


def test_default_provider_is_groq():
    assert DEFAULT_PROVIDER == "groq"


def test_default_model_is_llama():
    assert DEFAULT_MODEL == "llama-3.3-70b-versatile"


def test_provider_config_has_required_keys():
    for provider, config in PROVIDER_CONFIG.items():
        assert "base_url" in config, f"{provider}: base_url 없음"
        assert "api_key_env" in config, f"{provider}: api_key_env 없음"


def test_all_providers_present():
    assert "gemini" in PROVIDER_CONFIG
    assert "groq" in PROVIDER_CONFIG
    assert "openai" in PROVIDER_CONFIG
    assert "anthropic" in PROVIDER_CONFIG


def test_gemini_provider_config_structure():
    cfg = PROVIDER_CONFIG["gemini"]
    assert cfg["base_url"] == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert cfg["api_key_env"] == "GEMINI_API_KEY"


def test_invalid_provider_raises_value_error():
    with pytest.raises(ValueError, match="지원하지 않는 provider"):
        call_llm("unknown_provider", "model", "system", "user")


def test_missing_api_key_raises_environment_error():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(EnvironmentError, match="API 키 없음"):
            call_llm(DEFAULT_PROVIDER, DEFAULT_MODEL, "system", "user")


def test_call_llm_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "테스트 응답"}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch.dict("os.environ", {_DEFAULT_API_KEY_ENV: "test-key"}):
        with patch("core.llm_client.requests.post", return_value=mock_response):
            result = call_llm(DEFAULT_PROVIDER, DEFAULT_MODEL, "시스템 프롬프트", "유저 메시지")

    assert result == "테스트 응답"


def test_call_llm_http_error_raises():
    import requests as req

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = req.HTTPError("500 Error")

    with patch.dict("os.environ", {_DEFAULT_API_KEY_ENV: "test-key"}):
        with patch("core.llm_client.requests.post", return_value=mock_response):
            with pytest.raises(req.HTTPError):
                call_llm(DEFAULT_PROVIDER, DEFAULT_MODEL, "system", "user")


def test_fallback_map_has_gemini_to_groq():
    assert "gemini" in FALLBACK_MAP
    fb_provider, fb_model = FALLBACK_MAP["gemini"]
    assert fb_provider == "groq"
    assert fb_model == DEFAULT_MODEL


def test_gemini_503_or_429_triggers_fallback_to_groq():
    """Gemini 503/429 max_retries 소진 시 Groq으로 자동 전환 확인."""
    import requests as req

    groq_key_env = PROVIDER_CONFIG["groq"]["api_key_env"]
    gemini_key_env = PROVIDER_CONFIG["gemini"]["api_key_env"]

    overload_resp = MagicMock()
    overload_resp.status_code = 503
    overload_resp.headers = {}
    overload_resp.raise_for_status.side_effect = req.HTTPError("503")

    success_resp = MagicMock()
    success_resp.status_code = 200
    success_resp.json.return_value = {"choices": [{"message": {"content": "groq 응답"}}]}
    success_resp.raise_for_status = MagicMock()

    env = {gemini_key_env: "gemini-key", groq_key_env: "groq-key"}
    call_count = {"n": 0}

    def fake_post(url, **kwargs):
        call_count["n"] += 1
        if "generativelanguage" in url:
            return overload_resp
        return success_resp

    with patch.dict("os.environ", env):
        with patch("core.llm_client.requests.post", side_effect=fake_post):
            with patch("core.llm_client.time.sleep"):
                with patch("core.llm_client.get_cached", return_value=None):
                    with patch("core.llm_client.set_cached"):
                        result = call_llm("gemini", "gemini-2.0-flash", "sys", "usr", max_retries=0)

    assert result == "groq 응답"
    assert call_count["n"] == 2  # gemini 1회 + groq 1회


def test_fallback_not_repeated_on_second_503():
    """_fallback=True 상태에서 503 → 재귀 없이 HTTPError raise."""
    import requests as req

    groq_key_env = PROVIDER_CONFIG["groq"]["api_key_env"]

    overload_resp = MagicMock()
    overload_resp.status_code = 503
    overload_resp.headers = {}
    overload_resp.raise_for_status.side_effect = req.HTTPError("503")

    with patch.dict("os.environ", {groq_key_env: "groq-key"}):
        with patch("core.llm_client.requests.post", return_value=overload_resp):
            with patch("core.llm_client.time.sleep"):
                with pytest.raises(req.HTTPError):
                    # user를 다르게 → 캐시 키 충돌 방지
                    call_llm("groq", DEFAULT_MODEL, "sys", "usr_no_repeat", max_retries=0, _fallback=True)
