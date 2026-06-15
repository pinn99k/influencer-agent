# ADR 018 — LLM 캐싱 + Gemini 추가 + Department Layer
상태: 승인
일시: 2026-05-18
작성: 세션 18-19 결정

---

## 맥락

Spiral 1에서 세 가지 구조적 변경이 필요했다:
1. E2E 테스트 반복 시 API 비용 절감 필요
2. Groq llama-3.3-70b 한국어 품질 한계 → 모델 대안 필요
3. CEO가 4개 에이전트를 직접 관리하는 구조의 SRP 위반

## 결정

### 1. LLM 파일 캐시 (core/llm_cache.py)
- MD5 해시 기반 파일 캐시: (provider, model, system, user) → 응답 저장
- 위치: src/.cache/llm/*.json
- 동일 입력 재호출 시 API 호출 0, 토큰 0
- 프롬프트 변경 시 캐시 무효화 필요 (해시 변경됨)
- CACHE_ENABLED 플래그로 전역 제어

### 2. Gemini Provider 추가
- PROVIDER_CONFIG에 gemini 추가 (OpenAI 호환 엔드포인트)
- BaseAgent에 provider/model 클래스 변수 추가
- DEFAULT_PROVIDER/DEFAULT_MODEL로 SSoT 유지
- 에이전트별 모델 교체 가능 (클래스 변수 오버라이드)

### 3. Department Layer (departments/planning.py)
- CEO와 에이전트 사이에 기획본부(PlanningDepartment) 레이어 추가
- 컨텍스트 압축: 이전 에이전트 결과를 3줄 요약으로 압축 후 다음 에이전트에 전달
- 전략 브리핑: CEO에게 날것의 결과가 아닌 정제된 전략적 브리핑 전달
- 검증 + 재시도 로직을 department 레벨에서 관리

## 대안 검토

| 항목 | 선택 | 대안 | 선택 이유 |
|------|------|------|-----------|
| 캐시 | 파일 기반 | Redis/SQLite | MVP에 외부 의존성 불필요 |
| 브리핑 | LLM 3줄 요약 | 전체 전달 | 토큰 80-90% 절감, 정보 손실 최소 |
| 모델 전환 | provider 변수 | 하드코딩 | 에이전트별 독립 교체 가능 |

## 결과
- E2E 호출 수: 9+ → 4 고정 (CEO 최적화)
- 반복 테스트: 캐시로 API 비용 0
- 품질: 60/100 → 77/100 (프레임워크 개선)
- 테스트: 74 → 101 pass