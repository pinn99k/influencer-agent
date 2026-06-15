# 코덱스 실행 프롬프트 — Loop-002 (관리 중심 전환 백엔드)
# 이 파일 전체를 코덱스에게 그대로 붙여넣으면 된다.

---

## 너에게 주는 작업

너는 "인플루언서 에이전트" 프로젝트의 백엔드를 구현하는 개발자다.
작업 루트: D:\House\인플루언서_에이전트  (명령은 src/ 기준 실행)
파이썬 3.11+, 프레임워크 없음(Groq/OpenAI 직접 호출), DB 없음(마크다운 파일 기반).

목표: CEO 최종 리포트를 "산출물 단순 합본"에서 "LLM 종합 전략 보고서"로 바꾸고,
4주 실행계획을 구조화 API 로 노출한다. 그래야 UI가 "분석 뷰어"에서 "실행 관리"로
바뀐다. 전체 설계 근거는 아래 문서에 있다 — 구현 전 반드시 읽어라:

1. docs/workflow/loops/loop_002_관리중심전환.md        (범위/완료기준)
2. docs/workflow/step4_기능명세/CEO종합리포트_명세.md  (정밀 구현 명세 — 핵심)
3. docs/adr/028-관리중심-전환.md                       (왜 이렇게 결정했나)

읽고 참고할 기존 코드:
- src/agents/ceo.py (_finalize ~352행, _synthesize 신설 위치)
- src/core/report_builder.py (build_final_report — 폴백으로 유지)
- src/agents/manager.py (_extract_week_section — 파서 패턴 참고)
- src/agents/concept_planner.py (_STEP5_ASSEMBLE — 캘린더 '#### Week N' 포맷 출처)
- src/api/routes/reports.py (라우트/이름검증 패턴)
- src/core/config.py, src/api/main.py, src/core/file_manager.py(저장 파일명 확인)

---

## 반드시 지킬 규칙 (위반 금지)
- 한글이 포함된 파일은 Edit/Write/PowerShell 로 쓰지 말 것.
  반드시 파이썬 `Path(...).write_text(content, encoding="utf-8")` 로만 작성.
  (CJK 코드포인트 혼입 방지. 프롬프트 md, 테스트 등 전부 해당)
- 산출 텍스트에 외래문자(CJK 한자/일본어 가나/키릴) 혼입 0. 한국어+영어+숫자만.
- 기존 try/except 폴백을 제거하지 말 것. 새 LLM 경로도 실패 시 폴백 필수.
- 영문 경로 규칙: prompts/, knowledge/ 는 영문 디렉터리 (ADR 016).
- 작업 단위로 커밋하지 말고, 끝까지 구현 후 테스트 통과 상태로 둘 것.

---

## 구현 순서 (명세 그대로)
1. src/core/plan_extractor.py 신설 (명세 B2-1 코드 사용). LLM 미사용.
2. src/tests/test_plan_extractor.py (명세 테스트 항목). `cd src && python -m pytest -q` 통과.
3. src/api/routes/plan.py 신설 (명세 B2-2) + src/api/main.py 에 라우터 등록 (B2-3).
   * 먼저 file_manager 에서 최종리포트/컨셉기획 실제 저장 파일명 확인 후 상수 일치.
4. src/tests/test_plan_api.py (200/404/400).
5. src/prompts/ceo/final_report.md 신설 (명세 B1-1 의 6섹션 포맷 그대로, write_text).
6. src/core/config.py 에 CEO_REPORT_MAX_TOKENS = 2500 추가.
7. src/agents/ceo.py 에 _synthesize_final_report 추가 + _finalize 가 그것을 호출 (B1-2).
   _strip_foreign 존재 확인, 없으면 동일 패턴 신설.
8. 기존 테스트 회귀 수정: final_report 가 6섹션 종합으로 바뀌므로 이어붙이기 가정
   테스트가 있으면 갱신. `cd src && python -m pytest -q` 전체 통과(현재 247개 기준).
9. F2 프론트 컨트롤러 배선 (명세 F2): api.js getPlan, actions.js loadPlan +
   reset()에 State.plan=null, model.js State.plan, pushActivity job_completed 에서
   loadPlan 호출, main.js 부트 복구에 loadPlan 1회. node --check 로 문법 확인.
10. E2E 수동 확인: 가상 대상자(예: 김서연 미용사)로 분석 1회 ->
    최종리포트.md 가 6섹션 포함하는지, GET /api/plan/{name} 이 weeks/next_actions/kpi
    JSON 주는지 확인. (OPENAI_API_KEY 필요 — .env)

---

## 완료 보고 형식 (작업 끝나면 이렇게 알려라)
- 변경/신설 파일 목록
- pytest 결과 (총 N pass)
- /api/plan 샘플 JSON 1개
- 최종리포트.md 6섹션 헤더가 다 있는지 (있음/없음)
- 외래문자 검출 0 확인 여부
- 막힌 점/결정이 필요한 점 (있으면)

## 주의 — 뷰는 네 몫이 아니다
views.js / style.css (화면 디자인)는 Claude Design 이 별도로 한다.
너는 백엔드 + 컨트롤러(api/actions/model)까지만. State.plan 을 채워주면 끝.
