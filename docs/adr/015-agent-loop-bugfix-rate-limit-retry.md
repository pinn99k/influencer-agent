# ADR 015 — agent_loop 버그 수정 + rate limit 재시도

date: 2026-05-14 (세션 13)
status: 확정
spiral: 0-B

---

## 배경

Spiral 0-B end-to-end 실행 중 발견된 버그 2개와 rate limit 이슈.

---

## 이슈 1: _agent_loop max_iter 과소 설정

### 문제
`max_iter = len(AGENT_ORDER) + 2 = 6`으로 설정.
경쟁분석 validation 2회 실패 → loop 2회 추가 소모 → 모든 에이전트 완료 후에도
`else` 절 트리거 → 불필요한 조건 5 회장 보고 발생.

### 결정
`max_iter = len(AGENT_ORDER) * (MAX_RETRY + 2) + 2`
각 에이전트 최대 (MAX_RETRY + 1)회 시도 + loop overhead 포함.

---

## 이슈 2: _run_one_agent 내 chairman_report 후 loop 계속 실행

### 문제
`_run_one_agent` 내부에서 validation 2회 실패 후 `_report_to_chairman(5, context)` 호출 및 return.
그러나 `_agent_loop`는 다음 iteration을 계속 실행 — "회장 보고 = 즉시중단" 원칙 위반.

### 결정
`_run_one_agent` 호출 직후 `self.state.get("current_phase") == "회장보고대기"` 체크.
해당 시 `_agent_loop`에서 즉시 `return`.

---

## 이슈 3: Groq 429 rate limit

### 문제
무료 티어 30 RPM. goal_interpretation → next_decision → agent LLM 호출 연속 발생 시 429.
기존 `call_llm`에 재시도 없음 — 첫 429에서 바로 HTTPError raise.

### 결정
`call_llm`에 `max_retries=3` 재시도 추가.
`Retry-After` 헤더 우선, 없으면 지수 백오프 `2^(attempt+1)`.
재시도 대상: 429만. 그 외 에러는 즉시 raise.

---

## 영향

- `src/core/llm_client.py`: `import time` 추가, `call_llm` 재시도 로직 추가
- `src/agents/ceo.py`: `max_iter` 수식 변경, loop 내 회장보고 상태 체크 추가
- 기존 테스트 73개 전부 통과 (변경 없음)
