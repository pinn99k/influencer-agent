# ADR 030 — 측정 레이어(provenance) + MVP 하드닝
date: 2026-06-11 (세션 34)
status: 적용됨

## 배경
세션 31 로드맵이 측정·실험 설계를 1순위로 확정: 변수 귀속 없는 성과 데이터는
노이즈이고, 수동 운영을 AI 성과처럼 보이게 하면 포폴 진정성이 붕괴한다.
또한 풀 E2E 드라이런에서 이음새 버그(검증기 도메인단어 오판)와 견고성 공백
(채팅 비영속, 폴백 비가시, 테스트 오염)이 확인됐다.

## 결정
1. core/measure.py 신설 — 마크다운 테이블 기반(DB 없음 원칙 유지).
   - WeeklyKPI(주간), ContentEntry(게시물별 KPI+변수태깅: 주제/형식/길이/시간대),
     DecisionEntry(provenance actor=AI|사람 강제, 그 외 ValueError).
   - 저장: outputs/{이름}/.system/measure/. 집계: compare_by(변수 1개씩 — 실험
     원칙과 동일), weekly_report.
2. 의사결정 자동 후킹 — AI: ceo.run_reanalyze의 재실행 결정. 사람: PUT /direction.
   측정 실패는 파이프라인을 막지 않는다(swallow).
3. OutputValidator 반복 체크 보정 — n-gram 윈도우 4->8, 임계 20->10.
   근거: 4글자 윈도우는 도메인 단어(미용사의 '스타일링' x35)를 복붙으로 오판.
   실측 보정: 정상 출력 윈도우8 최대 4회 vs 복붙 12회+.
4. Track 0 폴백 가시화 — CEO 판단 7곳 폴백 시 'judgment_fallback' emit.
   폴백 자체(운영 안전장치)는 유지, 침묵만 제거.
5. 채팅 영속 — .system/chat_history.jsonl + ChatEngine 복원 + GET /chat/history.
6. 캐시버스팅 — GET / 가 로컬 자산에 부팅토큰 ?v= 주입(StaticFiles 앞 등록).

## 결과
343 pass (신규 30). 브라우저 E2E: 측정 입력->집계, 채팅 새로고침 복원. CJK 0.

## 참조
- 스펙: docs/workflow/2장_에이전트하네스/03_측정실험설계.md
- 로드맵: docs/workflow/2장_에이전트하네스/01_로드맵.md
