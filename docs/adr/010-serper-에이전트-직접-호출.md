# ADR 010 — Serper 호출 위치: 에이전트 직접 호출
date: 2026-05-13
status: 확정

## 결정
경쟁 분석 에이전트(`competition_analyst.py`)가 `core/serper_client.py`를 직접 호출한다.
CEO가 사전 주입하는 방식 채택 안 함.

## 선택지
- A: CEO가 Serper 결과를 미리 가져와 에이전트 context에 주입
- B: 경쟁 분석 에이전트가 직접 호출 ← 채택

## 근거
- 에이전트가 "외부 정보가 필요한지" 스스로 판단하는 구조가 역할 원칙에 맞음
- CEO가 주입하면 CEO가 검색 필요 여부를 대신 판단 → 역할 침범
- 경쟁 분석만 Serper 필요. CEO가 관여하면 불필요한 의존성 생김

## ⚠️ 미래 이슈 — Serper 제거 가능 시점
사용 모델이 네이티브 웹 검색을 지원하게 되면 (GPT-4o with search, Gemini grounding 등)
`serper_client.search()` 호출 제거 → 모델 네이티브 검색으로 대체 가능.

교체 범위: `competition_analyst.py` 단일 파일만 수정. CEO·다른 에이전트 무관.
교체 시 ADR 재작성 필수.

## 결과
- `competition_analyst.py` 내부에서 serper_client.search() 호출
- 결과를 프롬프트에 주입 후 LLM 호출
- Serper 결과 없을 시 fallback: LLM 추론 + `[데이터 부족 — 추론 기반]` 명시

---

## 영향 문서

| 문서 | 반영 내용 | 상태 |
|------|---------|------|
| `docs/workflow/step6_아키텍처/아키텍처.md` | §3-6 competition_analyst.py — run() 오버라이드로 Serper 직접 호출 | ✅ 반영 |
| `docs/workflow/step5_기술결정/흐름정리.md` | §4 Serper 호출 위치 결정 + 미래 이슈 명시 | ✅ 반영 |
