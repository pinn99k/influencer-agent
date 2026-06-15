# ADR 019 — FastAPI + SSE Web UI (Spiral 3)
상태: 승인
일시: 2026-05-19
작성: 세션 20 결정

---

## 맥락

Spiral 1 완료 (101 tests, E2E 2x PASS, 품질 77/100). CLI 파이프라인 검증 완료.
다음 단계: 핑구가 브라우저에서 CEO 활동을 실시간으로 보고, 회장 보고에 응답할 수 있는 Web UI.

## 결정

### 1. EventEmitter 패턴 — CEO-SSE 디커플링
- **선택:** EventEmitter 클래스가 queue.Queue + FileManager.append_log() 브릿지
- **대안:** CEO에 직접 SSE 로직 삽입 → 거부 (CLI 모드 깨짐, 테스트 복잡도 증가)
- **근거:** CEO에 event_emitter=None 기본값 → CLI 모드 무영향, 기존 101개 테스트 전량 통과

### 2. threading.Event — 회장 보고 블로킹
- **선택:** CEO 스레드가 threading.Event.wait(timeout=3600) 블록, POST /decision이 event.set()
- **대안:** asyncio 전환 → 거부 (CEO 전체 async 리팩토링 비용 과다)
- **근거:** 동기 CEO 코드 변경 최소화, 타임아웃으로 좀비 스레드 방지

### 3. SessionManager — 멀티잡 지원
- **선택:** dict[str, JobContext] + threading.Lock, MAX_CONCURRENT_JOBS=5
- **대안:** 싱글잡 글로벌 → 거부 (멀티잡 추가 비용 거의 0)
- **근거:** 각 CEO가 독립 FileManager/디렉토리 사용, 공유 상태 없음

### 4. Vanilla JS — 프레임워크 없음
- **선택:** 단일 app.js IIFE, EventSource API, 직접 DOM 조작
- **대안:** React/Vue → 거부 (빌드 스텝 추가, 컴포넌트 7개에 과잉)
- **근거:** claude-design-handoff.md 명시, CDN marked.js + DOMPurify로 XSS 방어

### 5. 보안
- CORS: localhost 전용 (127.0.0.1, localhost)
- 경로 탐색: _SAFE_NAME/_SAFE_FILE 화이트리스트 regex
- XSS: DOMPurify.sanitize(marked.parse()) — 모든 마크다운 렌더링
- 입력 검증: Pydantic BaseModel 전 엔드포인트

## 결과

- 신규 파일 13개 (api/ 패키지 + static/ 프론트엔드)
- 수정 파일 3개 (ceo.py, planning.py, config.py)
- 테스트: 기존 101 + 신규 20 = 121 pass (1 pre-existing fail)
- CEO 코드 변경: _emit() 헬퍼 + 6개 emit 포인트 + decision gate (~25줄)
