# Loop-002: 관리 중심 전환 (하이브리드 — 종합 리포트 + 실행 관리)
date:      2026-06-01
case:      A (계획된 이터레이션 — 핑구 승인)
from_step: 8 (Loop-001 V2 완료 이후)

## 배경 — 왜 이 루프인가
세션 28까지 V2(자율 에이전트)는 코드/테스트로 완료됐고, 세션 29에서
UI(Claude Design v3) 통합 후 핑구가 처음으로 직접 사용했다. 사용 직후 핑구 진단:

1. "분석 위주라 사용자가 뭘 해야 할지 모르겠다."
2. "CEO/매니저가 실행 계획을 짜줘야 하는 것 아니냐."
3. "UI가 결과물(산출물) 위주 → 사용자 관리 위주로 바뀌어야 한다."
4. "CEO 최종 리포트가 그냥 산출물 합쳐놓은 거라 별로다."

### 코드 확인 결과 (진단 근거)
- `report_builder.build_final_report` (report_builder.py:50) — context를 `---` 로
  단순 이어붙이기만 함. 종합/우선순위/실행 로드맵/executive summary 없음. LLM 미사용.
- 4주 실행계획(캘린더)은 이미 생성되나 `04_컨셉기획.md` 텍스트 안에 묻힘.
  매니저가 `weekly_card` 로 주차를 쪼개지만 UI 전면에 안 보임.
- 결론: 실행 기능은 거의 다 있는데 (a) 종합이 없고 (b) UI가 뷰어라 "관리"로 안 느껴짐.

## 제품 방향 결정 (핑구 확정, 세션 29)
| 항목 | 결정 |
|------|------|
| 정체성 | 하이브리드 — 종합 전략 리포트 + 주차별 실행 관리 둘 다 동등 비중 |
| 착수 | 리포트 재설계 + 관리중심 UI 를 묶어 한 번에 설계 |
| 구현 주체 | 코덱스(Codex) — 본 문서 기반 |
| UI 재작성 | Claude Design — 핸드오프_v4 기반 (views.js + style.css) |

## 범위 (IN)
- B1. CEO 종합 리포트 = LLM 종합 보고서로 재설계 (이어붙이기 폐기)
- B2. 실행계획 구조화 파서 + `GET /api/plan/{name}` API
- B3. CEO 리포트 포맷 고정 (B2 파서가 읽을 수 있도록 헤더 계약)
- F1. 관리중심 대시보드 재편 (할 일 / 4주 로드맵 / 다음 액션 전면)
- F2. 프론트 컨트롤러 배선 (api.js getPlan + actions.js loadPlan + State.plan)

## 범위 (OUT)
- 운영 중 CEO 실시간 채팅 백엔드(`POST /chat`) — 별도 작업 (현재 스텁 유지)
- Track B(Cross-review) / Track C(컨셉 심화) / Track A(마케팅 본부) — 본 루프 이후
- 실제 미용사 적용 — UI/리포트 검증 통과 후

## 복귀 step: 4 (기능명세) -> 6/7 (구현)
진행: Step 4(명세 본 루프 묶음) -> 코덱스 구현(백엔드+컨트롤러) -> Claude Design(뷰) -> 핑구 검증

## 신규/변경 파일 (요약 — 상세는 CEO종합리포트_명세.md)
신규:
- src/prompts/ceo/final_report.md          (CEO 종합 리포트 시스템 프롬프트)
- src/core/plan_extractor.py               (결정론적 캘린더/액션/KPI 추출)
- src/api/routes/plan.py                   (GET /api/plan/{name})
- src/tests/test_plan_extractor.py
- src/tests/test_plan_api.py
변경:
- src/agents/ceo.py                        (_finalize -> _synthesize_final_report 경유)
- src/core/report_builder.py              (build_final_report 는 폴백으로 유지)
- src/api/main.py                          (plan 라우터 등록)
- src/api/static/api.js                    (getPlan)
- src/api/static/actions.js               (loadPlan)
- src/api/static/model.js                 (State.plan)
- src/api/static/views.js + style.css     (Claude Design — 별도 핸드오프)

## 완료 기준
1. CEO 종합 리포트가 6개 섹션(결론/핵심결정/강점기회/4주로드맵/지금할일/KPI) 생성
2. 외래문자(CJK/JP/Cyrillic) 0 유지, OutputValidator 무회귀
3. `GET /api/plan/{name}` 가 weeks/next_actions/kpi JSON 반환 (가상 대상자 E2E)
4. plan_extractor 단위테스트 PASS (Week 파싱·중복없음·빈입력 폴백)
5. 대시보드가 [이번 주 할 일]·[4주 로드맵]·[다음 액션] 을 전면 표시, 분석4는 근거자료로
6. 기존 247 테스트 하위호환 유지 (+ 신규 테스트)
7. 핑구 브라우저 검증: "내일 뭘 찍을지" 가 화면에서 바로 보임

## 이전 이터레이션 영향
- final_report 포맷 변경 → 기존 최종리포트 의존 코드/테스트 점검
- plan_extractor 는 컨셉기획 `#### Week N` 헤더에 의존 → 컨셉 프롬프트 헤더 불변 유지
- LLM 종합 추가 → 1회 호출 비용 증가 (E2E 1회 측정)

## 참조
- 명세(코덱스용): docs/workflow/step4_기능명세/CEO종합리포트_명세.md
- UI 핸드오프: docs/workflow/step7_구현/핸드오프_v4_관리중심UI.md
- 코덱스 프롬프트: docs/workflow/step7_구현/코덱스_프롬프트_loop002.md
- ADR: docs/adr/028-관리중심-전환.md
- 실전적용(왜 실행이 핵심인가): docs/refs/실전적용_로드맵.md
