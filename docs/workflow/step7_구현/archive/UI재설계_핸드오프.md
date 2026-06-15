# UI 재설계 핸드오프 — Claude Design 용
# 목적: 인플루언서 에이전트 웹 UI 전면 재설계
# 작성: Claude(개발자), 세션 28 (2026-05-31)
# 읽는 대상: Claude Design (시각 디자인 + 마크업/CSS 담당)

---

## 0. 역할 분담 (먼저 읽어주세요)

| 주체 | 담당 | 산출물 |
|------|------|--------|
| Claude Design (당신) | 시각 디자인 + HTML 구조 + CSS | 정적 목업(HTML+CSS), 클래스/data 훅 계약 준수 |
| Claude 개발자 (나) | JS 로직 배선 (State/API/SSE) | 목업에 동작 주입, 백엔드 연결 |

**핵심: 당신은 마크업과 CSS만 주면 됩니다. JS 로직은 내가 붙입니다.**
정적 HTML + CSS로 "이렇게 생겨야 한다"를 보여주고, 아래 클래스/data-* 계약만
지켜주세요. 그 위에 내가 기존 State 스토어·API 클라이언트·SSE 스트림을 연결합니다.

---

## 1. 반드시 지킬 제약 (디자인이 어기면 안 되는 것)

### C-1. 화면 높이 고정 + 내부 패널만 스크롤
- 최상위 컨테이너는 height: 100vh 고정 (현재 버그: min-height라 콘텐츠만큼 늘어남)
- 페이지 전체 스크롤 금지. 스크롤은 각 패널(활동 목록, 산출물, 채팅) 내부에서만.
- 즉 헤더/푸터/패널 골격은 고정, 내용만 overflow-y: auto.

### C-2. CEO 상시 채팅 (가장 중요)
- 사용자는 입장 때만이 아니라 분석 완료 후에도 CEO와 계속 대화할 수 있어야 함.
- 대화 패널이 운영 화면(대시보드)에서도 상시 보여야 함.
- 위치/형태는 자유 (사이드 패널이든 하단 독이든) — 단 "항상 접근 가능"이 조건.

### C-3. 네비게이션 (어디서든 이동)
- 3개 공간을 자유롭게 오갈 수 있어야 함: 운영(대시보드/산출물) / 재분석 / 새 대상자.
- 현재 버그: 재분석 들어가면 기존 결과 화면으로 못 돌아옴. 단방향 금지.
- 명확한 네비(상단 메뉴든 사이드바든)로 양방향 이동 보장.

### C-4. 프론트/백엔드 철저 분리 (MVC) — 아키텍처 요구
- 프론트는 백엔드와 REST/SSE로만 통신. 백엔드 내부 구조에 의존 금지.
- 프론트 내부도 3계층으로 분리 (수정 용이성):
  - Model: 상태 저장소 (데이터만, DOM 모름)
  - View: 렌더 함수 (상태 -> DOM, 순수. API 직접 호출 금지)
  - Controller: API 호출 + SSE 수신 + 상태 갱신 (View와 Model 잇기)
- 디자인 산출물(마크업)은 View가 렌더할 구조여야 함. 인라인 이벤트/로직 넣지 말 것.
- 이유: 백엔드 바뀌어도 Controller만, 디자인 바뀌어도 View만 고치게.

### C-5. 클래스/data-* 훅 계약
- 동작이 붙어야 할 요소엔 안정적 class 또는 data-action 부여.
- 예: data-action="send-message", data-action="confirm-interview",
  data-action="open-report" data-report="01_대상분석.md" 등.
- 내가 이 훅으로 이벤트를 위임 바인딩함. 임의 변경 시 배선 깨짐 -> 아래 5절 참고.

---

## 2. 백엔드 계약 (프론트가 통신하는 전부)

### 2-1. REST 엔드포인트 (FastAPI, 모두 /api 프리픽스)

인터뷰 (서버 세션, 대화/제출 분리):
- POST /api/interview/start            -> {interview_id, type, message, turn_count}
- POST /api/interview/reply            body {interview_id, message}
    -> {type:"question|summary", message, extracted, sufficient, turn_count, can_submit}
- POST /api/interview/confirm          body {interview_id, approved, start_job}
    -> 미충족: {approved:false, can_submit:false, missing:[...]}  (대화 유지)
    -> 시작됨: {approved:true, subject, job_id}

실행/상태:
- POST /api/start                      body {subject} -> {job_id, status}
- GET  /api/status                     -> {jobs:[{job_id, influencer_name, status, error}]}
- GET  /api/status/{job_id}            -> {influencer_name, status, subject, reports, recent_events}
- GET  /api/stream/{job_id}            -> SSE 스트림 (아래 2-2)
- POST /api/decision/{job_id}          body {choice, reason}  (회장 결재)
- DELETE /api/job/{job_id}             (취소)

산출물:
- GET  /api/reports/{name}             -> {reports:["01_대상분석.md", ...]}
- GET  /api/reports/{name}/{filename}  -> {filename, content}  (마크다운 원문)

재분석:
- GET  /api/subjects                   -> {subjects:[{name, has_outputs, has_feedback, has_performance}]}
- POST /api/reanalyze                  body {name, feedback?} -> {job_id, status}
- GET/PUT /api/feedback/{name}         body {content}
- GET/PUT /api/performance/{name}      body {content}

### 2-2. SSE 이벤트 15종 (GET /api/stream/{job_id})
각 이벤트: {type, timestamp, ...payload}. 실시간 진행 표시에 사용.

- job_started          {influencer, mode?}
- plan_created         {subject}
- pipeline_started     {}
- agent_start          {agent, attempt}
- agent_done           {agent, detail}            # detail = 3줄 요약
- validation_fail      {agent, retry, rules}
- agent_questions_pending {escalated, data_requests}
- pipeline_completed   {}
- pipeline_completed_with_issues {failed_agents, total, passed}
- briefing_pending     {condition, briefing}      # 회장 결재 대기 -> 결재 UI 필요
- decision_received    {condition, choice}
- finalize_started     {}
- manager_notification {notification_type, content, week_num?}
    # notification_type: weekly_card | progress | performance_request | completion
- job_completed        {job_id}
- job_failed           {job_id, error}

### 2-3. 데이터 모델
- subject (11필드): 이름 직업 특기 성격 타겟연령대 SNS경험 목표 / 가용시간 촬영환경 카메라경험 예산
- 산출물 5개: 01_대상분석 02_경쟁분석 03_플랫폼추천 04_컨셉기획 / 최종리포트 (전부 .md)
- 매니저 알림 4종 (manager_notification.notification_type)

---

## 3. 화면 상태 인벤토리 (무엇이 언제 보이나)

| 상태 | 트리거 | 보여야 할 것 |
|------|--------|-------------|
| 대화 중 | 새 대상자 시작 | CEO 채팅 + 수집정보 패널. 제출버튼은 can_submit=true일 때만 |
| 분석 중 | confirm 후 job 시작 | 실시간 활동(SSE) + 진행상태. CEO 채팅 상시 유지 |
| 완료 | job_completed | 산출물 5개 + 매니저 알림 + 재분석 버튼. CEO 채팅 유지 |
| 결재 대기 | briefing_pending | 결재 모달/패널 (A/B 선택 -> POST decision) |
| 재분석 | 재분석 진입 | 기존 대상자 선택 + 피드백/성과 입력 + 시작. 결과로 복귀 가능 |

주의: "대화 중"과 "완료"가 배타적이면 안 됨 (C-2). 분석이 끝나도 대화는 살아있음.

---

## 4. 재사용 가능한 기존 자산 (처음부터 안 짜도 됨)

현재 src/api/static/ 에 있는 것 (내가 재배선할 부분):
- app.js: h() DOM 헬퍼, renderMd(마크다운), State 스토어, API 클라이언트, SSE 연결
- 이 로직들은 내가 MVC로 재구성. 디자인은 신경 안 써도 됨.
- 외부 의존: marked.js + DOMPurify (마크다운 렌더, CDN). 그대로 유지.

당신이 줄 것과 겹치지 않음 — 당신=겉(마크업/CSS), 나=속(로직).

---

## 5. 당신(Claude Design)이 산출할 것 + 경계

### 산출물 (이것만 주면 됩니다)
1. 정적 HTML 목업 — 위 화면 상태들을 표현하는 시맨틱 마크업
   (단일 index.html 또는 상태별 섹션. 실데이터 대신 더미 텍스트 OK)
2. CSS — 레이아웃(100vh 고정+내부 스크롤), 색/간격/타이포, 반응형
3. 동작 훅 — 동작 붙을 요소에 class/data-action (1절 C-5)

### 경계 (당신이 안 해도 되는 것)
- JS 로직 X (이벤트 핸들러, fetch, SSE, 상태관리 전부 내가)
- 백엔드 X
- 실데이터 연동 X (더미로 레이아웃만 보여주면 됨)

### 레이아웃은 자율
- C-1~C-5 제약만 지키면 화면 구성/배치/스타일은 당신 창의.
- 회장(핑구)이 "심플 최우선" 선호. 과한 장식보다 정보 위계 명확하게.

---

## 6. 수령 후 내 작업 (참고)
1. 목업 HTML 구조를 View 레이어 렌더 함수로 이식
2. Model(State) / Controller(API+SSE) 분리 재구성
3. data-action 훅에 이벤트 위임 바인딩
4. 라이브 스모크 + 브라우저 E2E 재테스트

---

## 7. 참조
- 현재 구현: src/api/static/{index.html, app.js, style.css}
- 백엔드 라우트: src/api/routes/{interview,ceo,stream,decision,reports,reanalyze}.py
- 비전(심플 우선): docs/refs/비전.md
- 현재 동작 확인: 세션 28 브라우저 E2E (전 흐름 PASS, 단 레이아웃 3문제)
