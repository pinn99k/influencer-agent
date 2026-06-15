# ADR 009 — llm_client.py provider 라우팅 (requests 직접 호출)
date: 2026-05-13
status: 확정

## 결정
`core/llm_client.py` 단일 진입점에서 provider 라우팅.
SDK 아닌 `requests` 직접 호출 (OpenAI 호환 API 공통 포맷 활용).

## 선택지
- A: provider별 SDK 설치 (groq, openai, anthropic 각각)
- B: requests 직접 + OpenAI 호환 포맷 공통화 ← 채택

## 근거
- OpenAI 호환 API (Groq, OpenAI, together.ai, Ollama 등)는 동일 HTTP 포맷 사용
- provider 교체 = base_url + api_key 변경만. 에이전트 코드 무관.
- SDK마다 인터페이스 다름 → 멀티 AI 확장 시 SDK 방식은 매번 코드 변경 필요
- `response.raise_for_status()` 한 줄로 4xx/5xx 처리 충분 (MVP 범위)
- Anthropic만 포맷 달라 별도 `_call_anthropic()` 함수 추가

## 인터페이스 고정
```python
call_llm(provider: str, model: str, system: str, user: str) -> str
```
이 시그니처가 바뀌면 전체 에이전트 코드 영향. 변경 시 ADR 재작성.

## 결과
- 에이전트 코드는 provider/model 파라미터만 바꾸면 AI 교체 완료
- Groq → GPT-4o 교체: 에이전트 파일 1줄 변경

---

## 영향 문서

| 문서 | 반영 내용 | 상태 |
|------|---------|------|
| `docs/workflow/step6_아키텍처/아키텍처.md` | §3-2 llm_client.py 설계 (PROVIDER_CONFIG, call_llm 시그니처) | ✅ 반영 |
| `docs/workflow/step5_기술결정/흐름정리.md` | §8 기술 결정 요약 — AI 호출: requests (OpenAI 호환) | ✅ 반영 |
