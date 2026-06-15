# ADR 023 — V2 자율 에이전트 확장 설계
date: 2026-05-28
status: accepted
session: 26

## Context
MVP V1 완료 (Spiral 0-A ~ 4-B). 1회성 리포트 생성기에서 자율 AI 기획사로 전환 필요.
핑구와 소크라테스식 분석 + 상세 Q&A를 통해 V2 확장 방향 확정.

## Decision

### 1. 코드 전략: 핵심 인프라 유지 + 에이전트 레이어 재설계
- 유지: core/ (llm_client, file_manager, config, serper_client 등), validators/, knowledge/, api/
- 재설계: agents/base_agent.py, agents/ceo.py, departments/planning.py, main.py, prompts/ 전체
- 신규: core/interview_engine.py, core/agent_context.py, agents/manager.py

### 2. AgentOutput — 결과물 + 메타데이터 반환
- 기존: 에이전트가 문자열만 반환
- 변경: AgentOutput(content, questions, comments, confidence, metadata) 반환
- 하위 호환: from_raw() lenient 파서 — JSON 실패 시 전체를 content로 처리

### 3. AgentContext — 에이전트별 파일 접근 범위 강제
- CEO: 전체 접근 + 요약 생성
- 하위 에이전트: 대상자 정보 + ceo_summary + 허용된 이전 산출물만

### 4. CEO 대화형 인터뷰 (InterviewEngine)
- 7개 필드 폼 대체 → 10턴+ 자연 대화
- LLM이 충분성 판단 (하드코딩 X)
- CLI 먼저, 웹 채팅 나중에

### 5. 프롬프트 전환
- ~24,600 단어 세부 지시서 → ~10,000 단어 역할 가이드
- FORMAT 헤더 불변 (OutputValidator 호환)
- EXAMPLES, SELF-CHECK → knowledge/ 파일 + validator로 이동

### 6. 매니저 에이전트
- 파이프라인 외부 서비스 (AGENT_CLASSES 미등록)
- CEO가 직접 호출, 알림/보고 전담
- EventEmitter → 웹 대시보드 연동

### 7. 구현 순서 (Spiral 5-A ~ 5-E)
- 5-A: AgentOutput + AgentContext 기반
- 5-B: 프롬프트 역할 가이드 전환
- 5-C: 대화형 인터뷰
- 5-D: 매니저 + 재분석 루프
- 5-E: 웹 통합

## Consequences
- V1 이월 항목(P0-3 성과기록, P0-4 재분석)은 V2 Spiral 5-D에 통합
- 기존 테스트는 AgentOutput.content 접근으로 점진적 수정 필요
- 프롬프트 전환 시 산출물 품질 모니터링 필수 (FORMAT 헤더 불변 보장)