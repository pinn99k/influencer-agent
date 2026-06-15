# E2E 테스트 예상 결과
# 파일: src/tests/e2e_gemini.py
# 실행: cd src && py tests/e2e_gemini.py
updated: 2026-05-16

---

## 전제 조건

| 항목 | 요구 사항 |
|------|-----------|
| GEMINI_API_KEY | .env 파일에 설정 필요 (미설정 시 Step 1에서 즉시 실패) |
| 네트워크 | generativelanguage.googleapis.com 접근 가능해야 함 |
| 실행 위치 | src/ 디렉터리에서 실행 (py tests/e2e_gemini.py) |
| 모델 | gemini-2.0-flash (DEFAULT_MODEL SSoT) |

---

## Step 1: API 연결 (예상 소요: 1~3초)

### 성공 출력 예시
```
[PASS] Step 1 PASS: LLM responded in 1.8s (1.8s)
  Provider : gemini
  Model    : gemini-2.0-flash
  Response : API 연결 성공했습니다.
```

### 실패 원인 및 조치

| 원인 | 증상 | 조치 |
|------|------|------|
| GEMINI_API_KEY 미설정 | EnvironmentError: API 키 없음: GEMINI_API_KEY | .env 파일에 GEMINI_API_KEY=<키> 추가 |
| 잘못된 API 키 | requests.HTTPError: 403 | Google AI Studio에서 유효한 키 재발급 |
| 네트워크 오류 | requests.ConnectionError | 인터넷 연결 및 방화벽 확인 |
| 응답 비어 있음 | ValueError: Empty response received | Gemini 서버 상태 확인 후 재시도 |

---

## Step 2: 대상분석 에이전트 단독 실행 (예상 소요: 2~5초)

### 성공 출력 예시
```
[PASS] Step 2 PASS: OutputValidator PASS, CJK 0개, 출력 850자 (3.2s)
  CJK 문자 수  : 0
  Validator    : PASS
```

### 성공 조건 체크리스트
- OutputValidator PASS (required_sections, required_keywords, count_checks, min_length 전부 통과)
- CJK/일본어 문자 0개 (BaseAgent.run()의 _FOREIGN_CHAR_RE.sub 자동 처리)

### 기대 출력 포맷 (OutputValidator.RULES 기준)
```markdown
## 대상 분석 결과
**대상자:** 김민수

### 강점
1. ...
2. ...
3. ...

### 약점
1. ...
2. ...
3. ...

### 차별점
- ...  (근거: ... 포함 필수)
```

### 필수 포함 항목 (누락 시 FAIL)

| 항목 | 검사 내용 |
|------|-----------|
| required_sections | ## 대상 분석 결과, ### 강점, ### 약점, ### 차별점 |
| required_keywords | **대상자:**, 근거: |
| count_checks | 강점 3개 이상, 약점 3개 이상 (번호 목록 1. 2. 3. 형식) |
| min_length | 출력 전체 300자 이상 |
| 대상자 이름 | 김민수 포함 |
| CJK 문자 | 0개 (잔존 시 FAIL) |

### 실패 원인 및 조치

| 원인 | 증상 | 조치 |
|------|------|------|
| FORMAT 불일치 | 필수 섹션 누락 | prompts/dept/planning/subject_analysis.md 프롬프트 튜닝 |
| 강점/약점 개수 부족 | 개수 부족 [강점]: 2 < 3 | 프롬프트에 반드시 3개씩 명시 강화 |
| CJK 잔존 | CJK 문자 N개 — BaseAgent 확인 | _FOREIGN_CHAR_RE 패턴 점검 |
| 너무 짧은 출력 | 최소 길이 미달 | LLM_TIMEOUT 또는 모델 응답 길이 확인 |
| rate limit | HTTPError 429 | 자동 재시도 1회 (최대 15초 대기) 후 실패 시 잠시 후 재실행 |

---

## Step 3: CEO 전체 E2E (예상 소요: 10~30초)

### 성공 출력 예시
```
  [대상분석] 실행 중… PASS (3.1s)
  [경쟁분석] 실행 중… PASS (4.8s)
  [플랫폼추천] 실행 중… PASS (3.5s)
  [컨셉기획] 실행 중… PASS (6.2s)

  --- 생성 파일 확인 ---
    v 01_대상분석.md — OK (924B)
    v 02_경쟁분석.md — OK (1143B)
    v 03_플랫폼추천.md — OK (756B)
    v 04_컨셉기획.md — OK (1821B)
    v 최종리포트.md — OK (2304B)

[PASS] Step 3 PASS: 4개 에이전트 PASS, 산출물 5개 파일 생성 (17.6s)
```

### 성공 조건 체크리스트
- CEO 종료 상태가 회장보고대기가 아닐 것
- 4개 에이전트 전부 context에 결과 저장됨
- 산출물 파일 5개 생성: 01_대상분석.md, 02_경쟁분석.md, 03_플랫폼추천.md, 04_컨셉기획.md, 최종리포트.md
- 각 에이전트 OutputValidator PASS

### 생성 파일 위치
```
src/outputs/김민수/
├── 산출물/
│   ├── 01_대상분석.md      ← SubjectAnalystAgent
│   ├── 02_경쟁분석.md      ← CompetitionAnalystAgent
│   ├── 03_플랫폼추천.md    ← PlatformRecommenderAgent
│   ├── 04_컨셉기획.md      ← ConceptPlannerAgent
│   └── 최종리포트.md       ← CEO ReportBuilder
├── 인수인계/
│   └── 인수인계_2026-XX-XX.md
└── .system/
    ├── ceo/
    │   ├── plan.md
    │   └── state.md
    └── agents/
        ├── 대상분석/raw_output.md + validation.md
        ├── 경쟁분석/raw_output.md + validation.md
        ├── 플랫폼추천/raw_output.md + validation.md
        └── 컨셉기획/raw_output.md + validation.md
```

### 에이전트별 OutputValidator 기준

| 에이전트 | 필수 섹션 수 | 필수 키워드 | 개수 체크 | 최소 길이 |
|---------|------------|-----------|----------|---------|
| 대상분석 | 4개 | **대상자:**, 근거: | 강점 3개, 약점 3개 | 300자 |
| 경쟁분석 | 4개 | **대상자:**, **데이터 출처:**, **검색 키워드:**, 연결: | 유사 포지션 3개 | 400자 |
| 플랫폼추천 | 4개 | **대상자:**, 출처: | — | 200자 |
| 컨셉기획 | 5개 | **대상자:**, **성격 반영:**, **차별점:**, **공백 연결:** | 아이디어 5개 | 600자 |

### 실패 원인 및 조치

| 원인 | 증상 | 조치 |
|------|------|------|
| 특정 에이전트 FORMAT 실패 (재시도 1회 후도 실패) | CEO → 회장보고 상태 (조건 5번) | 해당 에이전트 프롬프트 튜닝 후 재실행 |
| Gemini rate limit 반복 | 429 에러, 15초 대기 후 재시도 1회 | 잠시 후 재실행 또는 요청 빈도 조정 |
| 경쟁분석 데이터 출처 누락 | **데이터 출처:** 키워드 없음 | 경쟁분석 프롬프트에 출처 명시 지시 추가 |
| 컨셉기획 아이디어 부족 | 개수 부족 [아이디어]: N < 5 | 컨셉기획 프롬프트에 5개 정확히 지시 강화 |
| 산출물 파일 누락 | MISSING 표시 | FileManager.save_output() 호출 경로 확인 |

---

## 공통 디버깅 팁

### 에이전트별 단독 재실행
```bash
# src/ 디렉터리에서 실행
py agents/subject_analyst.py     # 대상분석만
py agents/competition_analyst.py # 경쟁분석만
```

### 이전 출력 파일 확인
```
src/outputs/김민수/.system/agents/{에이전트명}/raw_output.md   # LLM 원본 출력
src/outputs/김민수/.system/agents/{에이전트명}/validation.md   # 검증 결과
src/outputs/김민수/.system/agents/{에이전트명}/rework.md       # 재작업 지시 (발생 시)
```

### 회장보고 발생 시 확인 파일
```
src/outputs/김민수/.system/briefings/briefing_*_조건5.md
```
