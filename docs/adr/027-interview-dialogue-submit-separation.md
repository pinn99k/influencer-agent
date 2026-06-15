# ADR 027 — 인터뷰 대화/제출 분리 리팩토링

## 상태
승인됨 (세션 28, 2026-05-31)

## 맥락
핑구 UI 테스트에서 인터뷰 5개 문제 보고:
1. 새 대상자를 인터뷰로 받아야 하는데 구식 7필드 폼 탭이 공존
2. 2턴이면 충분한데 min_turns=5로 5턴 강제
3. 대화가 끝나도 분석이 시작되지 않음
4. 인터뷰 종료 후 산출물(결과)이 안 나옴
5. 대상분석 404 후 재입력하면 "인터뷰가 종료되었다" -> 의존성 분리 필요

핵심 원인(코드): InterviewEngine의 단일 state 변수가 '대화 진행'과 '종료/제출'을
한데 묶음. reply()가 한 번 summary를 내면 state='extracting'이 되고, 그 뒤
reply는 "이미 종료" 처리(L59). 즉 요약 표출 = 대화 종료로 잘못 결합.

핑구 지적: "대화랑 제출이 따로 분리되어야 한다. 대화 상태에 따라 제출 가능한지를
판단하면 된다."

## 결정 (대화/제출 분리)
- state 변수 제거 -> confirmed(종료 신호) 하나만 유지
- reply는 confirmed 전까지 항상 받는다. 요약을 내도 대화는 계속된다.
- can_submit()는 대화 상태와 독립, extracted 데이터로만 판단
  (이름 필수 + 필수 7개 중 4개 이상)
- confirm은 호출측(라우트)이 can_submit으로 게이트. 미충족 confirm은
  200 + approved:False + missing 반환(대화 유지), 400 아님
- min_turns 5 -> 3 (#2)
- 프론트: 탭 2개로 일원화([새 대상자(대화)] / [재분석]), 구식 폼 제거(#1).
  confirm 응답 3분기 처리: 미충족(대화 유지) / job 시작(대시보드 전환+SSE) / 오류

## 결과
- core/interview_engine.py 전면 리팩토링 (can_submit/missing_for_submit/confirmed)
- api/routes/interview.py: reply에 can_submit 노출, confirm 게이트
- api/static/app.js: 탭 일원화, confirmInterview 3분기, 제출버튼 can_submit 연동
- 인프로세스 스모크 전 흐름 검증:
  reply1 can_submit=False -> 이른 confirm approved=False/missing/job_id=None(대화유지)
  -> reply2 can_submit=True -> confirm job 시작 -> 종료 후 reply 404
- 테스트: test_interview_engine 20개 + test_interview_api 갱신, 전체 242 -> 247 pass
- CJK 오염 0

## 영향
- 기존 state 기반 테스트는 confirmed/can_submit 모델로 재작성
- 구식 7필드 폼 코드(viewEntry guide/formWrap)는 미사용 잔존(무해, 추후 제거 가능)
