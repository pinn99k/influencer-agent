# ADR 022 — Spiral 5-E 웹 통합 (대화형 인터뷰 + 매니저 알림)

## 상태
승인됨 (세션 28, 2026-05-30)

## 맥락
V2 Spiral 5-C에서 대화형 인터뷰 엔진(InterviewEngine)을, 5-D에서 매니저
에이전트(ManagerAgent)를 CLI 기준으로 완성했다. 그러나 웹은 여전히 V1 구조였다:
- 입력이 7필드 폼 고정 — 대화형 인터뷰를 웹에서 쓸 수 없음
- 매니저 알림(manager_notification)이 SSE로 흐르지만 프론트가 무시함
- 인터뷰는 다회 턴 대화로 상태(대화 이력, 추출 필드)를 들고 있어야 함

## 결정
1. 인터뷰는 **서버 세션 방식**으로 구현한다.
   - InterviewEngine 인스턴스를 interview_id로 서버가 보관 (api/routes/interview.py)
   - POST /api/interview/start | /reply | /confirm
   - confirm(approved=True) 시 수집된 subject dict를 그대로 CEO 파이프라인에 위임
     (session_mgr.start_job) — 폼 경로와 동일한 잡 생성
   - 스테이트리스 대비 토큰/페이로드 절감 + 추출 상태 일관성 확보
2. 매니저 알림은 **전용 알림 패널**로 보여준다.
   - 프론트 pushActivity가 manager_notification을 가로채 managerNotes에 누적
   - 대시보드 우측 레일에 viewManagerPanel (주간카드/진행보고/성과요청/완료요약)
3. 엔트리에 "대화 인터뷰" 탭을 기본으로 추가 (기존 폼/재분석 탭 유지).

## 결과
- 신규: api/routes/interview.py (서버 세션 레지스트리), tests/test_interview_api.py (6개)
- 변경: api/main.py (라우터 연결), app.js (인터뷰 채팅 UI + 매니저 패널 + API),
  style.css (채팅/패널 스타일), test_reanalyze_api.py (5-E 정적 자산 검증)
- 전체 226 -> 232 pass (신규 6). app.js node --check 통과. CJK 오염 0.
- 라이브 스모크: /api/interview/start 실 LLM 응답 확인, 3개 경로 등록, index 200

## 핵심 설계
- InterviewEngine은 변경 없음 — 웹은 얇은 세션 래퍼만 추가 (CLI와 로직 공유)
- 인터뷰 라우트는 한글 리터럴 0 — 필드 키는 core.interview_engine에서 import
- 매니저는 파이프라인 외부 서비스 유지 (AGENT_CLASSES 미등록), SSE 경유 단방향

## 대안
- 스테이트리스(매 요청에 대화 전체 전송): 토큰 증가 + 추출상태 재현 복잡 -> 기각
- 활동 피드에 매니저 알림 혼합: 보고가 일반 로그에 묻힘 -> 전용 패널 채택
- 폼 유지 + 인터뷰 CLI 전용: V2 "AI 기획사" 방향과 불일치 -> 기각

## 참조
- docs/refs/V2_설계문서.md
- docs/workflow/loops/loop_001_v2-자율에이전트.md
- src/api/routes/interview.py, src/api/static/app.js
