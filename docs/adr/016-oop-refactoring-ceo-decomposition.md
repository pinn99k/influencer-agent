# ADR 016 — OOP 리팩토링: CEO 분해 + AGENT_KEY_MAP 제거

date: 2026-05-15
session: 14
status: 확정

---

## 결정

CEO 클래스(355줄, 25메서드)를 SRP 원칙에 따라 4개 클래스로 분해한다.
AGENT_KEY_MAP dict를 제거하고 BaseAgent.context_key class var로 대체한다.

---

## 배경

코드 검토 결과 CEO 클래스가 4개의 서로 다른 책임을 혼재:
1. 에이전트 호출 순서/흐름 제어 (오케스트레이션)
2. 상태 초기화/갱신/저장
3. 텍스트 문서 조합 (briefing, report, handover 등)
4. 파일 로딩 (프롬프트, 지식)

CompetitionAnalystAgent.build_prompt가 부모와 서명 불일치 (LSP 위반).
AGENT_KEY_MAP은 에이전트 추가 시 수동 동기화 필요 (DRY 위반).

---

## 결정 내용

### CEO 분해

| 클래스 | 위치 | 책임 |
|--------|------|------|
| CEO | agents/ceo.py | 오케스트레이션만 |
| CEOStateManager | core/state_manager.py | 상태 관리 |
| ReportBuilder | core/report_builder.py | 문서 텍스트 조합 |
| PromptLoader | core/prompt_loader.py | 파일 로딩 |

CEO는 세 클래스를 __init__에서 생성해 보유. 위임 패턴.

### AGENT_KEY_MAP 제거

```python
# Before (ceo.py에 dict 하드코딩)
AGENT_KEY_MAP = {"대상분석": "대상_분석", ...}
context[AGENT_KEY_MAP[agent_name]] = result

# After (에이전트 클래스가 자신의 키 소유)
class SubjectAnalystAgent(BaseAgent):
    context_key = "대상_분석"

context[agent.context_key] = result
```

### CompetitionAnalystAgent LSP fix

```python
# Before (LSP 위반)
def run(self, context):          # 부모 run() override + LLM 중복 호출
def build_prompt(self, context, search_results=None):  # 서명 불일치

# After (LSP 준수)
def build_prompt(self, context): # 부모 서명과 동일
    search_results = serper_client.search(query)  # 내부에서 호출
    # 부모 run()이 build_prompt 호출 → LLM 호출
```

---

## 이유

- SRP: 단일 책임 원칙. 클래스당 변경 이유 1개.
- LSP: 서브클래스는 부모 계약을 지킨다.
- DIP: 에이전트가 자신의 context_key를 소유 → CEO가 dict에 의존하지 않음.
- DRY: 에이전트 추가 시 context_key만 설정하면 됨. 별도 dict 수정 불필요.

---

## 하위 호환성

- CEO.state property + _init_state/_update_state 메서드 유지 (테스트 참조)
- AGENT_KEY_MAP은 완전 제거 → 테스트 파일 일괄 업데이트

---

## 영향 범위

- 수정: agents/ceo.py, agents/base_agent.py, 에이전트 4개
- 신규: core/state_manager.py, core/report_builder.py, core/prompt_loader.py
- 테스트: 7개 파일 업데이트
