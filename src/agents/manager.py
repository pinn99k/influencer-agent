"""ManagerAgent -- 사용자 알림/보고 전용 서비스 (V2 Spiral 5-D).

BaseAgent를 상속하지 않는다 (파이프라인 에이전트 아님). AGENT_CLASSES 미등록.
CEO가 호출하며, 전략 판단 없이 구조화 데이터를 사용자 친화적 포맷으로 변환하고
EventEmitter 알림 + .system/manager/ 저장만 수행한다. (템플릿 기반, LLM 선택)
"""
import re
import datetime

_ORDER = ["대상분석", "경쟁분석", "플랫폼추천", "컨셉기획"]
_KEY = {"대상분석": "대상_분석", "경쟁분석": "경쟁_분석",
        "플랫폼추천": "플랫폼_추천", "컨셉기획": "컨셉_기획"}


class ManagerAgent:
    def __init__(self, file_manager, llm_client_fn=None, event_emitter=None):
        self._fm = file_manager
        self._llm = llm_client_fn
        self._emitter = event_emitter

    # ---------- 주간 실행 카드 ----------
    def generate_weekly_card(self, calendar_output: str, week_num: int) -> str:
        if week_num not in (1, 2, 3, 4):
            raise ValueError(f"week_num은 1~4여야 합니다: {week_num}")
        section = self._extract_week_section(calendar_output or "", week_num)
        if not section:
            card = (f"## 이번 주 할 일 (Week {week_num})\n\n"
                    "캘린더가 아직 생성되지 않았습니다. 먼저 전체 분석을 실행해주세요.\n")
        else:
            card = (
                f"## 이번 주 할 일 (Week {week_num})\n\n"
                f"### 촬영 목록\n{section}\n\n"
                "### 준비물\n- 스마트폰 거치대, 자연광 위치 확인\n- 고객 촬영 동의서 (해당 시)\n\n"
                "### 업로드 체크리스트\n- [ ] 해시태그 포함 (산출물 참고)\n- [ ] 캡션 작성\n"
                "- [ ] 최적 시간대 업로드\n- [ ] 썸네일 확인\n"
            )
        self._fm.save_manager_output(f"weekly_card_week{week_num}.md", card)
        self.notify("weekly_card", card, week_num=week_num)
        return card

    def _extract_week_section(self, calendar: str, week_num: int) -> str:
        m = re.search(rf"####\s*Week\s*{week_num}\b", calendar)
        if not m:
            return ""
        rest = calendar[m.end():]
        nxt = re.search(r"\n####\s|\n###\s", rest)
        body = rest[:nxt.start()] if nxt else rest
        lines = [ln.strip() for ln in body.splitlines()
                 if ln.strip().startswith(("1.", "2.", "3.", "4.", "5.", "-", "*"))]
        return "\n".join(lines)

    # ---------- 진행 보고서 ----------
    def generate_progress_report(self, agent_results: dict, validation_results: dict) -> str:
        agent_results = agent_results or {}
        validation_results = validation_results or {}
        lines = ["## 진행 보고\n", "### 분석 상태"]
        for name in _ORDER:
            if _KEY[name] in agent_results:
                v = validation_results.get(name, {})
                score = v.get("quality_score")
                if score is not None:
                    tag = f"완료 (품질 {score}/100)"
                elif v.get("passed"):
                    tag = "완료"
                else:
                    tag = "완료 (검증 미통과)"
                lines.append(f"- {name}: {tag}")
            else:
                lines.append(f"- {name}: 대기중")
        lines.append("\n### 다음 단계\n- 완료된 산출물은 산출물/ 폴더에서 확인하세요.")
        report = "\n".join(lines)
        date = datetime.date.today().isoformat()
        self._fm.save_manager_output(f"progress_report_{date}.md", report)
        self.notify("progress", report)
        return report

    # ---------- 성과 입력 요청 ----------
    def request_performance_input(self, week_num: int) -> str:
        if week_num not in (1, 2, 3, 4):
            raise ValueError(f"week_num은 1~4여야 합니다: {week_num}")
        msg = (
            f"## 성과 기록 요청 (Week {week_num})\n\n아래 항목을 입력해주세요:\n\n"
            "- 팔로워 수: ___\n- 이번 주 총 조회수: ___\n- 가장 반응 좋았던 콘텐츠: ___\n"
            "- 댓글/DM 특이사항: ___\n- 특이사항/피드백: ___\n"
        )
        self._fm.save_manager_output(f"performance_request_week{week_num}.md", msg)
        self.notify("performance_request", msg, week_num=week_num)
        return msg

    # ---------- 완료 요약 ----------
    def generate_completion_summary(self, final_report: str) -> str:
        platform_line = self._first_line(final_report or "", ["1순위", "인스타그램", "유튜브", "틱톡"])
        head = ["## 분석 완료 요약\n"]
        if platform_line:
            head.append(f"### 핵심 결과\n- {platform_line}\n")
        body = [
            "### 지금 바로 할 3가지",
            "1. 산출물 검토 (산출물/ 폴더의 4개 분석 + 최종리포트)",
            "2. 이번 주 실행 카드 확인 (.system/manager/weekly_card_week1.md)",
            "3. 첫 콘텐츠 촬영 시작\n",
            "### 산출물 위치",
            "- 전체 분석: outputs/{name}/산출물/",
            "- 주간 실행 카드: outputs/{name}/.system/manager/",
        ]
        text = "\n".join(head + body)
        self.notify("completion", text)
        return text

    def _first_line(self, text: str, keywords) -> str:
        for ln in text.splitlines():
            s = ln.strip().lstrip("#*- ").strip()
            if s and any(k in s for k in keywords):
                return s[:120]
        return ""

    # ---------- 알림 ----------
    def notify(self, notification_type: str, content: str, week_num=None) -> None:
        data = {"notification_type": notification_type, "content": content}
        if week_num is not None:
            data["week_num"] = week_num
        if self._emitter:
            self._emitter.emit("manager_notification", data)
        else:
            print(f"[매니저] 알림: {notification_type}")
