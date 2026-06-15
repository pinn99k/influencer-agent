"""InterviewEngine -- CEO 대화형 인터뷰 (V2 Spiral 5-C, 리팩토링).

설계 원칙 (대화와 제출 분리):
- 대화(reply)와 제출(confirm)은 독립이다.
- reply는 확정(confirmed) 전까지 항상 받는다. 요약을 냈다고 대화가 끝나지 않는다.
- confirm은 '지금 제출 가능한가(can_submit)'만 판단해서 처리한다.
- can_submit = 이름 수집됨 + 필수 필드 최소 개수 충족.

LLM은 매 턴 JSON({type, message, extracted_so_far, sufficient})으로 응답한다.
"""
import json
import re
from dataclasses import dataclass, field

from core.llm_client import call_llm_messages
from core.prompt_loader import PromptLoader
from core.config import LLM_MAX_TOKENS
from core.direction import DirectionProfile

_REQUIRED_FIELDS = ["이름", "직업", "특기", "성격", "타겟연령대", "SNS경험", "목표"]
_EXTENDED_FIELDS = ["가용시간", "촬영환경", "카메라경험", "예산"]
_ALL_FIELDS = _REQUIRED_FIELDS + _EXTENDED_FIELDS

# 방향 필드 — subject(대상자)와 분리. extracted 에는 담기되 get_subject 로는 새지 않는다.
# 사용자가 정한 전략 방향을 인터뷰에서 함께 수집(선택지 제안). DirectionProfile 로 변환.
_DIRECTION_FIELDS = ["콘텐츠방향", "핵심목표", "중점전략"]

_PLACEHOLDER = "정보 없음"

# 제출 가능 최소 조건:
#   - 이름은 절대 필수 (작업 폴더명)
#   - 필수 7개 중 최소 4개 수집 (이름 포함)
_NAME_FIELD = "이름"
_MIN_REQUIRED_FOR_SUBMIT = 4

_STOP_WORDS = ("그만", "종료", "끝낼", "다 말했", "다 얘기했", "이제 됐")


@dataclass
class InterviewResponse:
    type: str                                  # "question" | "summary" | "error"
    message: str
    extracted: dict = field(default_factory=dict)
    sufficient: bool = False                    # CEO가 충분하다고 본 신호 (요약 표출용)
    turn_count: int = 0
    can_submit: bool = False                    # 지금 제출(분석 시작) 가능한가


class InterviewEngine:
    """CEO 주도 대화형 인터뷰 엔진.

    상태 변수는 confirmed(종료 여부) 하나뿐. 대화 진행과 제출 가능 여부는
    분리되어 있으며, 제출 가능 여부는 매 시점 extracted로부터 계산한다.
    """

    def __init__(self, provider: str = "openai", model: str = "gpt-4o",
                 max_turns: int = 25, min_turns: int = 3):
        self.provider = provider
        self.model = model
        self.max_turns = max_turns
        self.min_turns = min_turns
        self.conversation: list = []           # assistant/user 턴만 보관
        # subject 필드 + 방향 필드를 함께 추출 스키마에 둔다 (방향은 get_subject 로 안 샌다)
        self.extracted: dict = {f: _PLACEHOLDER for f in _ALL_FIELDS + _DIRECTION_FIELDS}
        self.confirmed = False                 # True가 되면 대화 종료 (제출 완료)
        self.turn_count = 0
        self._system = PromptLoader.load_prompt("ceo/interview")

    # ---------- 제출 가능 판단 (대화 상태와 독립) ----------
    def can_submit(self) -> bool:
        """현재까지 수집된 정보로 분석을 시작할 수 있는가.

        대화가 몇 턴이든, 요약을 냈든 안 냈든 무관 — 오직 데이터로만 판단.
        """
        name = (self.extracted.get(_NAME_FIELD) or "").strip()
        if not name or name == _PLACEHOLDER:
            return False
        filled = sum(
            1 for f in _REQUIRED_FIELDS
            if (self.extracted.get(f) or "").strip() not in ("", _PLACEHOLDER)
        )
        return filled >= _MIN_REQUIRED_FOR_SUBMIT

    def missing_for_submit(self) -> list:
        """제출까지 부족한 것 (안내 메시지용)."""
        gaps = []
        name = (self.extracted.get(_NAME_FIELD) or "").strip()
        if not name or name == _PLACEHOLDER:
            gaps.append(_NAME_FIELD)
        filled = sum(
            1 for f in _REQUIRED_FIELDS
            if (self.extracted.get(f) or "").strip() not in ("", _PLACEHOLDER)
        )
        if filled < _MIN_REQUIRED_FOR_SUBMIT:
            gaps.append(f"필수 정보 {_MIN_REQUIRED_FOR_SUBMIT - filled}개 더")
        return gaps

    # ---------- public ----------
    def start(self) -> str:
        """CEO 첫 인사 + 첫 질문 반환."""
        kickoff = [
            {"role": "system", "content": self._system},
            {"role": "user", "content": "(상담을 시작합니다. 따뜻하게 인사하고 첫 질문을 해주세요.)"},
        ]
        parsed = self._parse_llm_response(self._invoke(kickoff))
        greeting = parsed.get("message") or "안녕하세요! 먼저 성함과 하시는 일을 여쭤봐도 될까요?"
        self.conversation.append({"role": "assistant", "content": greeting})
        return greeting

    def reply(self, user_message: str) -> InterviewResponse:
        """사용자 답변 처리 -> 다음 질문 또는 요약.

        confirmed(제출 완료) 전까지는 항상 대화를 받는다. 요약을 냈더라도
        사용자가 더 말하면 계속 이어간다 (대화/제출 분리).
        """
        if self.confirmed:
            return InterviewResponse("error", "이미 분석이 시작되어 인터뷰가 종료되었습니다.",
                                     dict(self.extracted), False, self.turn_count,
                                     self.can_submit())
        text = (user_message or "").strip()
        if not text:
            return InterviewResponse(
                "question", "혹시 질문이 어려우셨나요? 편하게 한두 마디라도 들려주세요.",
                dict(self.extracted), False, self.turn_count, self.can_submit())

        self.conversation.append({"role": "user", "content": text})
        self.turn_count += 1

        parsed = self._parse_llm_response(self._invoke(self._build_messages()))
        self._merge_extracted(parsed.get("extracted_so_far", {}))
        message = parsed.get("message", "")
        self.conversation.append({"role": "assistant", "content": message})

        # 충분 신호: LLM이 충분하다고 보고 + 최소 턴 충족 + 실제 제출 가능
        sufficient = (
            bool(parsed.get("sufficient"))
            and self.turn_count >= self.min_turns
            and self.can_submit()
        )
        rtype = parsed.get("type", "question")
        # 요약은 '표출'일 뿐 종료가 아니다. 사용자는 계속 대화 가능.
        out_type = "summary" if (sufficient and rtype == "summary") else "question"
        if out_type == "question" and not message:
            message = self._summary_text() if sufficient else "조금만 더 말씀해 주시겠어요?"

        return InterviewResponse(out_type, message, dict(self.extracted),
                                 sufficient, self.turn_count, self.can_submit())

    def confirm(self, approved: bool, corrections=None) -> dict:
        """제출. approved=True면 확정(대화 종료), 아니면 수정만 반영하고 대화 유지.

        주의: 제출 가능 여부 판단은 호출측(라우트)이 can_submit으로 가드한다.
        여기서는 approved일 때 confirmed=True로 종료만 처리한다.
        """
        if approved:
            self.confirmed = True
            return self.get_subject()
        # 수정 요청 — 대화는 계속 (confirmed 아님)
        if corrections:
            if isinstance(corrections, dict):
                for k, v in corrections.items():
                    if k in self.extracted and v:
                        self.extracted[k] = v
            else:
                self.conversation.append({"role": "user", "content": f"수정 요청: {corrections}"})
                parsed = self._parse_llm_response(self._invoke(self._build_messages()))
                self._merge_extracted(parsed.get("extracted_so_far", {}))
        return self.get_subject()

    def get_subject(self) -> dict:
        """7+4 필드 dict. 미수집은 '정보 없음'. (방향 필드는 제외 — get_direction 참조)"""
        return {f: (self.extracted.get(f) or _PLACEHOLDER) for f in _ALL_FIELDS}

    def get_direction(self) -> DirectionProfile:
        """인터뷰에서 수집한 방향 필드를 DirectionProfile 로 변환.

        미수집(_PLACEHOLDER)은 빈 값으로 처리. 중점전략은 쉼표/슬래시/가운뎃점으로 분리."""
        def val(f: str) -> str:
            v = (self.extracted.get(f) or "").strip()
            return "" if v == _PLACEHOLDER else v

        focus_raw = val("중점전략")
        focus = [s.strip() for s in re.split(r"[,/·]", focus_raw) if s.strip()] if focus_raw else []
        return DirectionProfile(
            content_focus=val("콘텐츠방향"),
            target_goal=val("핵심목표"),
            strategy_focus=focus,
        )

    def save_conversation(self, path) -> None:
        from pathlib import Path as _P
        lines = []
        for m in self.conversation:
            who = "CEO" if m["role"] == "assistant" else "사용자"
            lines.append(f"**{who}:** {m['content']}")
        _P(path).write_text("\n\n".join(lines), encoding="utf-8")

    # ---------- internal ----------
    def _invoke(self, messages) -> str:
        try:
            return call_llm_messages(self.provider, self.model, messages,
                                     max_tokens=LLM_MAX_TOKENS)
        except Exception as e:
            print(f"[InterviewEngine] LLM 호출 실패 ({e})")
            return ""

    def _build_messages(self) -> list:
        msgs = [{"role": "system", "content": self._system}]
        msgs.append({"role": "system",
                     "content": "현재까지 추출된 필드: " + json.dumps(self.extracted, ensure_ascii=False)})
        msgs.extend(self.conversation)
        if self._check_force_extract():
            msgs.append({"role": "system",
                         "content": "최대 턴에 도달했습니다. 지금까지 정보로 type=summary, sufficient=true로 요약하세요."})
        return msgs

    def _parse_llm_response(self, raw: str) -> dict:
        if not raw:
            return {"type": "question", "message": "(응답 지연) 다시 한 번 말씀해주시겠어요?",
                    "extracted_so_far": {}, "sufficient": False}
        s = raw.strip()
        if s.startswith("```"):
            parts = s.split("```")
            if len(parts) >= 2:
                s = parts[1]
                if s.startswith("json"):
                    s = s[4:]
                s = s.strip()
        start, end = s.find("{"), s.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(s[start:end])
                if isinstance(data, dict):
                    return data
            except (ValueError, TypeError):
                pass
        return {"type": "question", "message": raw.strip(),
                "extracted_so_far": {}, "sufficient": False}

    def _check_force_extract(self) -> bool:
        return self.turn_count >= self.max_turns

    def _merge_extracted(self, new_fields) -> None:
        if not isinstance(new_fields, dict):
            return
        for k, v in new_fields.items():
            if k not in self.extracted:
                continue
            if v in (None, "", "null", _PLACEHOLDER):
                continue
            self.extracted[k] = v

    def _summary_text(self) -> str:
        lines = ["지금까지 말씀해주신 내용을 정리했습니다."]
        for f in _ALL_FIELDS:
            lines.append(f"- {f}: {self.extracted.get(f)}")
        lines.append("이대로 분석을 시작할까요? 더 말씀하실 게 있으면 계속 이어가셔도 됩니다.")
        return "\n".join(lines)
