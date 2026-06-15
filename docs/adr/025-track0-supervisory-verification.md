# ADR 025 — 트랙 0: 감독층(CEO/매니저) 검증

## 상태
승인됨 (세션 28, 2026-05-30)

## 맥락
세션 28까지 "V2 완료"라 했으나, 측정된 것은 하위 워커 4개뿐이었다.
그 위 감독층(CEO 자율 루프 + 매니저)은 한 번도 실 LLM으로 검증된 적 없었다.
핑구(회장)가 이 공백을 지적: "4개 하위 에이전트만 설계한 것 아니냐,
그걸 총괄 감독할 CEO/매니저 검증은 안 하냐."

추가로, 코드 self-review에서 CEO의 LLM 판단 메서드 6개가 전부 try/except로
실패 시 조용히 폴백함을 확인. 즉 "CEO.run()이 통과했다"는 사실은
아무것도 보장하지 않는다 (폴백으로 굴러간 건지 실제 판단인지 구분 불가).

## 결정
트랙 0을 "품질 점수 측정"이 아니라 "폴백이 아닌 실제 발화 + 판단 타당성"
검증으로 설계한다. 4단계(V-1~V-4).

### 검증 범위 정정 (코드 확인)
CEO.run() -> _agent_loop -> PlanningDepartment.run() 위임 구조라,
CEO 본인의 _decide_next / _judge_quality / _check_llm_chairman_conditions는
라이브 경로에서 호출되지 않는 죽은 코드(테스트만 참조)였다.
실제 발화하는 CEO 판단은 _interpret_goal / _build_ceo_summary /
_handle_agent_questions / _check_briefing_for_chairman 4개.

## 결과

### V-1 — 폴백 계측 E2E (실 LLM, 가상 미용사 박지훈)
- tests/e2e_ceo_quality.py 신규 — call_llm/call_llm_messages 래핑해 예외(폴백 트리거) 계측
- 결과: run_error NONE, llm exceptions 0 (폴백 0건), call_llm 12회
- _interpret_goal 폴백 False, _build_ceo_summary 폴백 False(240자 실제 요약)
- 워커 4개 전부 완료, 매니저 산출물 2개 생성
- 결론: CEO 판단이 폴백이 아닌 실제 LLM 발화임을 증명

### V-2 — 판단 타당성
- ceo_summary: 대상자 강점(활발함/빠른스타일링/남성컷) + 타겟 + 플랫폼 + 가용시간
  구체 반영 -> 타당, 품질 양호
- plan.md: 4에이전트 순서/완료 추적 정상. 단 체크리스트 수준(전략 깊이는 얕음 - 개선여지)
- 질문 라우팅: 충분한 입력에선 질문 미발생(세션27 기진단대로 정상)
- 질문 분류 실 LLM 검증: tests/test_ceo_questions_live.py 신규(빈약입력으로
  STRATEGIC/TACTICAL/DATA 3분류 실제 발화 확인, OPENAI_API_KEY 없으면 skip)

### V-3 — 매니저 결정론적 정확성
- tests/test_ceo_supervisory.py — generate_weekly_card(cal, N)가 정확히 N주차만
  추출(인접 주 누출 없음), Week4가 다음 섹션 침범 안 함, progress_report가
  agent_results에 있는 에이전트만 표기. 매니저는 LLM 미사용이므로 '품질'이 아니라
  '추출/포맷 정확성'으로 검증.

### V-4 — 회장 보고 조건 갭 기록
- AUTO_CONDITIONS={5,9}, LLM_CONDITIONS={3,6}. 명세는 10개 조건이나 코드 발화는 제한적
- 라이브 경로에서 확실히 발화하는 건 조건 9(실행 진입)뿐
- 조건 3/6 담당 _check_llm_chairman_conditions는 _agent_loop에서 미호출(죽은 코드)
- 갭을 test_ceo_supervisory.py에 어셋션으로 고정 -> 향후 배선 시 의도적으로만 변경됨
- 어디까지 구현할지는 회장 결정 사항(미구현이지 버그 아님)

## 영향
- 전체 232 -> 242 pass (신규: 감독층 9 + 질문 live 1)
- 코드 변경 없음 (검증/계측만). CEO 폴백 try/except는 운영 안전장치로 보존
- 발견: e2e 하네스가 stdout UTF-8 미래핑 시 cp949 크래시(em-dash) -> 하네스에만 수정
  (production main.py/api.main은 이미 래핑됨, 제품 버그 아님)

## 다음
- 트랙 0 완료. 다음은 트랙 B(Cross-review) 또는 plan.md 전략 깊이 개선(V-2 발견)
- 결과 파일 src/_e2e_ceo_*.txt 보존(핑구 확인 후 삭제)
