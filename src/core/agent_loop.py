"""core/agent_loop.py -- 최소 자율 도구 호출 루프 (Phase 2 / Phase C).

call_llm_tools로 도구를 노출하고, 모델이 고른 도구를 실행해 결과를 다시 먹여
모델이 다음 행동을 스스로 정하게 한다(루프). 정지 조건:
  - finish 도구 호출 / 도구 없는 응답 / max_iter(가드레일).
"""
import json

from core.llm_client import call_llm_tools


class AgentLoop:
    def __init__(self, executor, tools, system_prompt, *,
                 provider: str = "openai", model: str = "gpt-4o",
                 max_iter: int = 8, event_emitter=None):
        self.executor = executor
        self.tools = tools
        self.system_prompt = system_prompt
        self.provider = provider
        self.model = model
        self.max_iter = max_iter
        self._emitter = event_emitter
        self.messages: list = []

    def _emit(self, t, d=None):
        if self._emitter:
            self._emitter.emit(t, d or {})

    def run(self, user_msg: str) -> dict:
        self.messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_msg},
        ]
        iterations = 0
        stop_reason = "max_iter"   # overwritten when the loop stops cleanly
        for iterations in range(1, self.max_iter + 1):
            msg = call_llm_tools(self.provider, self.model, self.messages, self.tools)
            self.messages.append(msg)
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                stop_reason = "no_tool"
                break
            for tc in tool_calls:
                fn = (tc.get("function") or {}).get("name", "")
                raw_args = (tc.get("function") or {}).get("arguments") or "{}"
                try:
                    args = json.loads(raw_args)
                except (ValueError, TypeError):
                    args = {}
                self._emit("tool_call", {"name": fn, "args": args})
                result = self.executor.execute(fn, args)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": result,
                })
            if self.executor.finished:
                stop_reason = "finish"
                break
        if stop_reason == "max_iter":
            self._emit("loop_max_iter", {"max_iter": self.max_iter})
        self._emit("loop_stopped", {"reason": stop_reason, "iterations": iterations})
        return {
            "iterations": iterations,
            "finished": self.executor.finished,
            "ran": list(self.executor.ran),
            "stop_reason": stop_reason,
            "messages": self.messages,
        }
