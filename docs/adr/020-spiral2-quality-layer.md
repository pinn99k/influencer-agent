# ADR 020: Spiral 2 품질 레이어
날짜: 2026-05-21
상태: 승인

## 배경
Spiral 1 E2E PASS 후 실제 산출물 품질 측정 결과 61/100.
프롬프트 강화만으로 65/100 — 근본적 개선 필요.

## 결정

### 1. 생성 모델 Gemini 전환
- DEFAULT_PROVIDER: groq → gemini
- DEFAULT_MODEL: llama-3.3-70b-versatile → gemini-2.0-flash
- 이유: Groq llama3-70b 한국어 품질 한계 (문장 미완성, 날조)

### 2. _judge_quality LLM 평가
- 생성: Gemini / 평가: Groq — 자기 평가 편향 방지
- QUALITY_THRESHOLD=65: 미달 시 재시도 (MAX_RETRY=1)
- 재시도 소진 시 진행 (파이프라인 차단 방지)
- JSON 파싱 실패 시 건너뜀 (non-fatal)

### 3. 경쟁분석 검색 전략
- 단일 쿼리 → 3-쿼리 크리에이터 전용 검색
- "유튜버 OR 크리에이터 OR 채널" 접미어 강제
- 플랫폼/도구 결과 필터링 제약 프롬프트 추가

### 4. Validator 강화
- 불완전 문장 감지 (한국어 종결어미 체크)
- 반복 n-gram 감지 (4-char x15+ threshold)
- 미확인 과다 체크 (경쟁분석 3회 이상)

## 대안 검토
- 모델 미전환 + 프롬프트만 강화: 4점 개선으로 불충분
- 전 에이전트 GPT-4o: 비용 과다, MVP 원칙 위배
- _judge_quality 없이 규칙만: 의미적 품질 판단 불가

## 영향
- LLM 호출 +4 (에이전트당 1 judge call): 총 16-17 calls/run
- Gemini 무료 티어 사용 (일일 quota 존재)
- 기존 101+ 테스트 전부 호환 유지
