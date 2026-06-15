# Loop-001: MVP V2 자율 에이전트 시스템 확장
date:      2026-05-28
case:      A (계획된 이터레이션)
from_step: 7 CODE 완료 (세션 26 MVP 완료 선언)

## 추가 범위

### 신규 기능
1. **대화형 인터뷰** — CEO가 10턴+ 대화로 사용자 정보 추출 (7필드 폼 대체)
2. **에이전트 자율성** — AgentOutput(결과+질문+첨언), AgentContext(접근권한), 역할 가이드 프롬프트
3. **매니저 에이전트** — 사용자 알림/보고 전담 (파이프라인 외부)
4. **재분석 루프 완성** — P0-3(성과기록) + P0-4(--reanalyze) 구현

### 변경 범위
- agents/base_agent.py — AgentOutput 반환
- agents/ceo.py — 인터뷰 통합 + 질문/첨언 처리
- departments/planning.py — AgentOutput 처리
- main.py — 인터뷰 모드
- prompts/ 전체 — 역할 가이드 전환

### 신규 파일
- core/interview_engine.py
- core/agent_context.py
- agents/manager.py
- prompts/ceo/interview.md
- prompts/ceo/question_handler.md
- prompts/manager/notification.md

## 복귀 step: 3 (MVP 범위 재정의)
진행: Step 3 → 4 → 6 → 7 (Spiral 5-A ~ 5-E)

## 완료 기준
1. InterviewEngine CLI 테스트 — 10턴 대화 후 subject dict 추출
2. AgentOutput — 4개 에이전트 모두 결과+질문+첨언 반환
3. AgentContext — 범위 밖 접근 차단 테스트 통과
4. ManagerAgent — 주간 카드/보고 생성
5. 재분석 모드 — --reanalyze 실행 성공
6. 기존 테스트 117개+ 통과 (하위 호환)
7. E2E 품질 80+ (OpenAI gpt-4o)

## 이전 이터레이션 영향
- AgentOutput으로 반환 타입 변경 → 기존 string 반환 코드 전부 수정
- 프롬프트 축소 → 산출물 품질 모니터링 필요
- PlanningDepartment가 AgentOutput 파싱해야 함

## 진행 상태 (세션 28 갱신)
- 5-A AgentOutput+AgentContext: 완료 (세션 27)
- 5-B 프롬프트 역할가이드 + CEO 질문처리: 완료 (세션 27)
- 5-C 대화형 인터뷰 엔진: 완료 (세션 27)
- 5-D 매니저 + 재분석 루프: 완료 (세션 27)
- 5-E 웹 통합: 완료 (세션 28) — 서버세션 인터뷰 API + 채팅 UI + 매니저 알림 패널

**Loop-001 V2 전체 완료. 다음 루프: 실인플루언서 적용 (Spiral 5 운영).**
