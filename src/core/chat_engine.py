"""ChatEngine — context-aware multiturn CEO chat (U4).

The CEO chats with the client grounded in the influencer's strategy context
(final report or the 4 analysis outputs, plus direction/performance/feedback).
When the client states a direction/preference, it is captured so the caller can
save it (방향.md) and reflect it in the next reanalysis.

Design:
- SRP: this engine only conducts the conversation. Persistence (방향.md) and
  HTTP/session live in FileManager and the route layer respectively.
- DIP/testability: the LLM is `call_llm_messages` at module scope, so tests
  patch `core.chat_engine.call_llm_messages`. FileManager is injected.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from core.llm_client import call_llm_messages
from core.config import LLM_MAX_TOKENS
from core.prompt_loader import PromptLoader

_MAX_SECTION_CHARS = 1500
_FALLBACK_GREETING = "안녕하세요, 이 기획사의 대표예요. 전략에 대해 궁금한 점이나 원하시는 방향을 말씀해주세요."
_FALLBACK_REPLY = "(응답 지연) 잠시 후 다시 한 번 말씀해주시겠어요?"


@dataclass
class ChatResponse:
    message: str
    captured_direction: str = ""   # non-empty when the client set a direction
    history_len: int = 0


class ChatEngine:
    def __init__(self, file_manager, provider: str = "openai", model: str = "gpt-4o"):
        self.fm = file_manager
        self.provider = provider
        self.model = model
        self.history: list = []          # [{"role": "user"|"assistant", "content": str}]
        self._system = PromptLoader.load_prompt("ceo/chat")
        self._context_block: str | None = None
        # Restore prior turns from disk so a server restart keeps the conversation
        # (mock FileManagers in unit tests may return non-lists — ignore those).
        try:
            prev = self.fm.load_chat_history()
            if isinstance(prev, list):
                self.history = prev
        except Exception:
            pass

    def _persist(self, role: str, content: str) -> None:
        try:
            self.fm.append_chat_message(role, content)
        except Exception:
            pass   # persistence must never break the conversation

    # ---------- public ----------
    def start(self) -> str:
        kickoff = "(대화를 시작합니다. 분석 결과를 바탕으로 따뜻하게 인사하고, 어떤 방향을 원하는지 물어봐 주세요.)"
        parsed = self._parse(self._invoke(self._messages(extra_user=kickoff)))
        greeting = parsed.get("message") or _FALLBACK_GREETING
        self.history.append({"role": "assistant", "content": greeting})
        self._persist("assistant", greeting)
        return greeting

    def reply(self, user_message: str) -> ChatResponse:
        text = (user_message or "").strip()
        if not text:
            return ChatResponse("메시지를 입력해주세요.", "", len(self.history))

        self.history.append({"role": "user", "content": text})
        self._persist("user", text)
        parsed = self._parse(self._invoke(self._messages()))
        message = parsed.get("message") or _FALLBACK_REPLY
        direction = (parsed.get("direction_update") or "").strip()
        self.history.append({"role": "assistant", "content": message})
        self._persist("assistant", message)
        return ChatResponse(message, direction, len(self.history))

    # ---------- context ----------
    def _context(self) -> str:
        if self._context_block is None:
            self._context_block = self._build_context_block()
        return self._context_block

    def _build_context_block(self) -> str:
        parts: list[str] = []
        report = self.fm.load_final_report()
        if report:
            parts.append("# 최종 전략 리포트\n" + report)
        else:
            for key, text in (self.fm.load_existing_outputs() or {}).items():
                if text:
                    parts.append(f"# {key}\n{text[:_MAX_SECTION_CHARS]}")
        direction = self.fm.load_direction()
        if direction:
            parts.append("# 사용자가 정한 방향\n" + direction)
        perf = self.fm.load_performance_record()
        if perf:
            parts.append("# 성과 기록\n" + perf)
        feedback = self.fm.load_feedback()
        if feedback:
            parts.append("# 피드백\n" + feedback)
        return "\n\n".join(parts) if parts else "(아직 분석 산출물이 없습니다.)"

    # ---------- llm ----------
    def _messages(self, extra_user: str | None = None) -> list:
        system = self._system + "\n\n# 컨텍스트(이 인플루언서의 현황)\n" + self._context()
        messages = [{"role": "system", "content": system}] + list(self.history)
        if extra_user:
            messages.append({"role": "user", "content": extra_user})
        return messages

    def _invoke(self, messages) -> str:
        try:
            return call_llm_messages(self.provider, self.model, messages,
                                     max_tokens=LLM_MAX_TOKENS)
        except Exception as e:
            print(f"[ChatEngine] LLM 호출 실패 ({e})")
            return ""

    def _parse(self, raw: str) -> dict:
        s = (raw or "").strip()
        if not s:
            return {"message": "", "direction_update": ""}
        if s.startswith("```"):
            parts = s.split("```")
            if len(parts) >= 2:
                s = parts[1]
                if s.startswith("json"):
                    s = s[4:]
        s = s.strip()
        try:
            data = json.loads(s)
            if isinstance(data, dict) and "message" in data:
                return data
        except (json.JSONDecodeError, ValueError):
            pass
        # Not JSON -> treat the raw text as the message (graceful).
        return {"message": s, "direction_update": ""}
