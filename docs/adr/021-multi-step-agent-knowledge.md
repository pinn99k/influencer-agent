# ADR 021: Multi-step Agent Execution + Knowledge Enrichment
date: 2026-05-21
session: 24
status: accepted

## Context
에이전트 품질 점수가 평균 51/100으로 실사용 불가 수준.
원인 분석 결과 3가지 구조적 문제 발견:
1. 에이전트 간 컨텍스트 전달 시 3-line 압축으로 정보 손실
2. Knowledge 파일이 에이전트당 1-2개, 70-100줄로 얕음
3. 에이전트당 1회 LLM 호출로 "bulk generation" 모드 강제

## Decision

### Phase A: 컨텍스트 복원
- departments/planning.py의 _inject_summaries()를 no-op으로 변경
- LLM_MAX_TOKENS: 4000 → 8000 (Gemini 1M 컨텍스트 활용)
- CEO_MAX_TOKENS: 400 → 1000

### Phase B: Knowledge 강화
- 에이전트당 knowledge 파일을 2-3개로 확장 (총 7개 신규)
- 미용사 도메인 특화 지식 포함 (사례, 성격별 전략, 플랫폼 수익화 등)

### Phase C: Multi-step Agent Execution
- BaseAgent에 Template Method Pattern 적용:
  - get_steps() → 빈 리스트면 기존 _single_call() (backward compatible)
  - 오버라이드하면 _multi_step_call() 실행
- SubjectAnalyst: 4-step (강점 → 약점 → 차별점 → 조립)
- CompetitionAnalyst: 4-step (추출 → 포지셔닝 → 공백 → 포맷)
- ConceptPlanner: 5-step (컨셉 → 아이디어 → 캘린더 → 가이드 → 조립)
- PlatformRecommender: 변경 없음 (single call 유지)

## Consequences
- Good: 각 step이 하나의 사고에 집중 → 품질 향상 기대
- Good: Knowledge가 system prompt에 자동 주입 → 도메인 판단 근거 강화
- Good: backward compatible → 기존 에이전트 영향 없음
- Bad: LLM 호출 횟수 증가 (4→13 calls per run) → 비용/시간 증가
- Bad: Gemini 무료 티어 rate limit에 더 취약 → fallback 필요
- Risk: Gemini 503 overload 시 전체 파이프라인 정지 → fallback 미구현 상태

## Alternatives Considered
1. 프롬프트만 강화 (코드 변경 없음) → 구조적 한계로 기각
2. 모든 에이전트를 gpt-4o로 교체 → 비용 과다, 핑구 승인 필요
3. RAG 도입 → MVP 복잡도 증가, 현재 불필요
