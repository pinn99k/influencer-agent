# ADR 012 — 웹 프레임워크: FastAPI + SSE
date: 2026-05-13
status: 확정 (Spiral 3 적용)

## 결정
웹 UI(Spiral 3)는 FastAPI + SSE(Server-Sent Events)로 구현한다.

## 선택지
- A: Streamlit — 빠름, 데이터앱 특화, 커스텀 UI 제한
- B: FastAPI + HTML + SSE ← 채택
- C: Flask + HTML — 비동기 없음

## 근거
- 에이전트 4개 순차 실행 시 30~60초 소요 예상 → 실시간 진행 상태 표시 필수
- 비동기 없이 실시간 스트리밍 불가 → Streamlit·Flask 제외
- SSE(단방향)가 우리 케이스에 적합: 서버→클라이언트 실시간 이벤트 스트림
- FastAPI: OpenAPI 문서 자동 생성, 포트폴리오 임팩트, 나중에 외부 연동 확장 용이

## SSE 한계 및 대응
SSE는 단방향이라 클라이언트→서버 통신은 별도 REST endpoint 필요:
- 실행 시작: POST /run
- 진행 상황: GET /stream/{job_id} (SSE)
- 실행 취소: DELETE /run/{job_id}
- 회장 보고 응답: POST /decision/{job_id}

## 결과
- Spiral 3에서만 적용 (CLI는 Spiral 0~2)
- SSE 로그 소스: outputs/{인플루언서명}/.system/logs/{날짜}.jsonl

---

## 영향 문서

| 문서 | 반영 내용 | 상태 |
|------|---------|------|
| `CLAUDE.md` | Stack → UI 항목 (CLI Spiral 0~2, 웹 UI Spiral 3) | ✅ 반영 |
| `docs/workflow/step6_아키텍처/아키텍처.md` | §7 Spiral 3 비동기 처리 (asyncio.to_thread + SSE 엔드포인트 4개) | ✅ 반영 |
| `docs/workflow/step5_기술결정/흐름정리.md` | §8 기술 결정 요약 — 웹 프레임워크: FastAPI + SSE | ✅ 반영 |
| `api/main.py`, `api/routes/run.py` | Spiral 3 구현 대상 (미작성) | ⬜ 미작성 |
