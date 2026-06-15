"""call_llm_tools 프리미티브 단위 테스트 (requests mock)."""
from unittest.mock import patch, MagicMock

from core.llm_client import call_llm_tools


def test_passes_tools_and_returns_message():
    msg = {"role": "assistant", "content": None,
           "tool_calls": [{"id": "c1", "type": "function",
                           "function": {"name": "run_subject_analysis", "arguments": "{}"}}]}
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"choices": [{"message": msg}]}
    tools = [{"type": "function", "function": {"name": "run_subject_analysis", "parameters": {}}}]
    with patch("core.llm_client.requests.post", return_value=resp) as mp:
        out = call_llm_tools("openai", "gpt-4o", [{"role": "user", "content": "hi"}], tools)
    assert out == msg
    sent = mp.call_args.kwargs["json"]
    assert sent["tools"] == tools
    assert sent["tool_choice"] == "auto"
    assert sent["messages"][0]["content"] == "hi"
