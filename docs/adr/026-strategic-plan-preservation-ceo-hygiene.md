# ADR 026 — 전략 plan 보존 + CEO 언어 위생

## 상태
승인됨 (세션 28, 2026-05-31)

## 맥락
트랙 0 V-2에서 "plan.md가 얕다"고 봤는데, 소크라테스식으로 원인을 캐니
깊이 문제가 아니라 구조 버그였다:
- _interpret_goal(L195)이 LLM으로 풍부한 전략 plan을 생성해 save_plan
- 그러나 _agent_loop 끝(L332) _update_plan -> build_plan(완료/남은 체크리스트)이
  plan.md를 덮어씀 -> LLM 전략이 진행상황 트래커에 소실
즉 V-2에서 본 "체크리스트 plan"은 LLM 출력이 아니라 그걸 덮어쓴 것이었다.

추가로, 수정 후 E2E에서 CEO 레이어의 언어 위생 누락을 발견:
- plan.md에 중국어 간체(리스크 뜻 단어), 일본어(없음 뜻 단어) 혼입
- 워커는 base_agent._FOREIGN_CHAR_RE로 외국어를 거르지만 CEO의
  _interpret_goal / _build_ceo_summary는 그 필터를 적용하지 않았다

## 결정
1. 전략(plan.md, 불변)과 진행상황(progress.md, 가변)을 분리 (SSoT)
   - FileManager.save_progress 추가, _update_plan이 progress.md에 저장
   - build_plan은 '진행 상황' 트래커로 라벨 변경
2. CEO LLM 출력 2곳에 base_agent._FOREIGN_CHAR_RE 동일 적용 (언어 위생 일관성)
3. goal_interpretation.md 완료기준 보강: 차별화 각도/위험요소/에이전트별 구체 지시

## 결과 (E2E 재검증, 가상 미용사 박지훈)
- plan.md preserves strategy: True / bare checklist: False / progress.md exists: True
- plan.md에 초기가설 + 전략방향("핵심=남성 미용 전문가 신뢰 구축") +
  에이전트별 구체 핵심지시 보존
- plan.md CJK=0 JP=0 (외국어 오염 제거), 전체 문서 CJK=0 JP=0
- 폴백 0건 유지, 워커4/매니저 정상, 전체 242 pass

## 소크라테스식 CEO/매니저 재판단 결론
- CEO _interpret_goal: 전략 plan 풍부 + 보존 + 언어 위생 OK -> 역할 수행 양호
- CEO _build_ceo_summary: 대상자 특성 구체 반영 -> 양호
- CEO 질문처리: 충분입력 시 미발생(정상), 빈약입력 실LLM 분류 검증됨
- 매니저: 캘린더 추출 정확, 대상자 특기 반영한 실제 쇼츠 제목 생성 -> 양호
- 남은 갭(미구현, 버그 아님): 회장보고 조건 9개 미발화(ADR 025 V-4),
  plan의 죽은코드 판단 메서드(_decide_next 등은 PlanningDepartment에 위임됨)

## 영향
- 변경: core/file_manager.py(save_progress), agents/ceo.py(_update_plan,
  _interpret_goal/_build_ceo_summary 필터), core/report_builder.py(라벨),
  prompts/ceo/goal_interpretation.md(완료기준)
- 신규 파일: outputs/{name}/.system/ceo/progress.md (진행상황)
- 회귀 없음 242 pass. CJK 오염 0
