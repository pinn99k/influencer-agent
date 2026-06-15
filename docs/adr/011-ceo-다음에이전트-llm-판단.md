# ADR 011 — CEO 다음 에이전트 결정: LLM 판단 방식
date: 2026-05-13
status: 확정

## 결정
CEO가 에이전트 실행 순서를 하드코딩하지 않는다.
각 에이전트 결과 수신 후 CEO LLM이 다음 행동을 재판단한다.

## 선택지
- A: 코드에서 순서 고정 (대상분석 → 경쟁분석 → 플랫폼추천 → 컨셉기획 for loop)
- B: CEO LLM이 매 결과 후 다음 에이전트 재판단 ← 채택

## 근거
CEO/02_판단루프.md 명시:
"다음 단계 판단 자체가 CEO 오케스트레이터의 핵심 역할이다."
"에이전트 순서가 하드코딩되면 상황 변화에 대응할 수 없다."

## 판단 조건
- 에이전트 결과 OK 판정 직후 (매번 실행)
- 회장 보고 결정 수신 후 재개 시

## 판단 범위
허용:
- 에이전트 실행 순서 변경
- 결과 빈약 시 이전 에이전트 보완 재요청
- 컨텍스트 보완 후 재실행

금지:
- 4개 에이전트 중 건너뛰기 (MVP 전부 필수)
- 5번째 에이전트 임의 추가
- 회장 보고 조건 우회

## 참고 도메인 (CEO 판단 시 참조)
1. 현재 context 상태 (누적 결과물)
2. 대상자 목표 (context["대상자"]["목표"])
3. 인플루언서 마케팅 도메인 지식 (src/knowledge/ (ADR 014 반영) — Spiral 0-A 시 작성)
4. plan.md (현재 전략)

## 판단 출력 형식 (src/prompts/ceo/next_decision.md)
```
next_action: run | rework | complete | chairman_report
target_agent: {에이전트명}
reason: {이유 한 줄}
```

## 결과
- ceo.py 루프는 for loop 아닌 while loop + LLM 판단으로 구현
- 순서 변경 발생 시 plan.md에 이유 기록 필수

---

## 영향 문서

| 문서 | 반영 내용 | 상태 |
|------|---------|------|
| `docs/workflow/step6_아키텍처/아키텍처.md` | §3-8 ceo.py _decide_next() + _agent_loop() while 구조 | ✅ 반영 |
| `docs/workflow/step5_기술결정/흐름정리.md` | §3 CEO 다음 에이전트 판단 — LLM 방식 (판단 조건·범위·도메인) | ✅ 반영 |
| `src/prompts/ceo/next_decision.md` | 판단 출력 형식 정의 (Spiral 0-A 시 작성) | 완료 |
