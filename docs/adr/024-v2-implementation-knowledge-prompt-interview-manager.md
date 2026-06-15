# ADR 024 — V2 구현: Knowledge 재구성 + 역할가이드 프롬프트 + 인터뷰 + 매니저
date: 2026-05-30
status: accepted
session: 27
related: ADR 023 (V2 설계)

## Context
ADR 023에서 설계한 V2 자율 에이전트를 실제 구현하며 4가지 구조 결정을 확정했다.

## Decisions

### 1. Knowledge 도메인 taxonomy 재구성
- dept/planning/{에이전트}/ 하위를 프레임워크/(범용 사고틀) · 사례/(업종 구체) · 출력/(산출물 스캐폴딩)로 분리.
- BaseAgent._load_knowledge: glob → rglob (하위 폴더 재귀 로딩).
- 범용(프레임워크)과 구체(사례) 분리로 에이전트 분할 시 도메인 지식 재사용 가능.
- management/ 트리는 이미 정돈됨 → 유지. 컨벤션은 knowledge/README.md.

### 2. 역할가이드 프롬프트 전환 (4개 에이전트)
- 지시서형(~270줄) → 역할가이드형: ROLE/GOAL/THINKING_GUIDE/ACCESS/OUTPUT/CONSTRAINTS.
- FORMAT 헤더·키워드는 불변 (OutputValidator.RULES 매칭 유지) — 검증 회귀 0.
- [EXAMPLES]/[FORMAT 상세] → knowledge/{에이전트}/출력·예시로 이동. [SELF-CHECK]는 validator가 대체.
- 범용 프레임워크 8개 신규로 context_quality 보강 (얇은 프롬프트의 품질 안전판).
- E2E 품질 82~90 확인. 컨셉 다양성 nudge로 3컨셉 소재 분화.

### 3. AgentOutput + AgentContext (5-A) + ceo_summary/질문처리 (5-B)
- AgentOutput.from_raw 관대한 파싱(블록/평문/깨진JSON), PlanningDepartment 단일 지점 파싱.
- AgentContext.build_context: 에이전트별 read 키 + outputs→context_key 매핑 필터.
- CEO _build_ceo_summary, _handle_agent_questions(STRATEGIC/TACTICAL/DATA 3분류).
- 진단: 7필드 입력에선 에이전트가 [추정]으로 임무완료 → questions는 안전망(실발생은 인터뷰 후).

### 4. 대화형 인터뷰(5-C) + 매니저(5-D)
- call_llm_messages(멀티턴) 신규. InterviewEngine: 7+4 필드, LLM 충분성 판단, subject dict 파이프라인 호환.
- ManagerAgent: BaseAgent 미상속·파이프라인 외부 서비스. 알림/보고 전담(템플릿 기반, LLM 선택).
- CEO가 완료/재분석 시 매니저 호출. EventEmitter manager_notification. CLI는 파일저장 폴백.

## Consequences
- 전체 217 테스트 그린. serper 이중검색·브리핑 충돌 등 기존 버그도 해소.
- 신규 4필드(가용시간 등)는 인터뷰로 수집되나 4개 에이전트 프롬프트의 적극 참조는 향후 과제.
- 5-E(웹 통합)와 실인플루언서 적용이 남음.
