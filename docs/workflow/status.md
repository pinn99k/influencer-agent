# Workflow Status
project: 인플루언서 에이전트
updated: 2026-06-15 (세션 37 — 문서 동기화 + GitHub 공개 준비)

## current_step: 8 -> 2장 진입 — 1장(워크플로우 MVP) 졸업 선언, 2장(자율 에이전트 하네스) 시작
## 2장 진행: Phase A(디렉티브 seam)+Phase C(도구 호출 루프) 완료 — 시스템이 처음으로 도구+루프+피드백+가드레일로 '에이전트'화 (세션 35)

## 세션 37 (2026-06-15) — 문서 동기화 + GitHub 공개 준비
현재 상태(세션 36) 기준으로 공개 문서를 일괄 동기화하고, 모노레포에서 분리한 공개용 클린 카피를 준비.
- 문서 동기화: README.md(테스트 268->373, ADR 30->32, 측정 레이어 구현완료, 세션 35~36 진행 반영),
  docs/취준_프로젝트요약.md(세션 34->36 갱신), MVP범위/최종목표(현황 주석), 본 status.
- GitHub 공개 준비: 새 클린 폴더(influencer-agent)로 복제(.env / outputs / _e2e_*.txt / 캐시 /
  취준문서 / 벨로그초안 / task_08 / Claude_Design 제외) -> git init -> 초기 커밋. Public, 한글 README.
- 결정: ADR 033(공개 레포 분리 + 문서 동기화). 알려진 정리거리: ADR 030 번호 중복(2파일).

## 현재 세션 포커스 (세션 36 마감 — 실사용자 산출물 풀 수정)
실사용자 예으니 피드백 재검토 -> "테스트 통과 != 실사용 가능" 확인 -> 생성기 소스 수정 +
실제 gpt-4o 재생성 검증. 373 pass (370->373).
- 문제(핑구): 예으니 산출물이 370테스트/웹E2E 통과에도 실사용 불가. 결함 4종 진단:
  (1) 최종리포트 이름 오염(예으니->예은이 타인명) (2) 플레이스홀더 "정보 없음" 노출
  (3) KPI 날조(팔로워1,000/조회5,000, 본인목표 1만 무시) (4) 콘텐츠 목록 3개
  (영상아이디어/4주캘린더/리포트로드맵) 제목 제각각 -> "뭘 할지" 혼란.
  근본원인: "PASS"의 정의가 구조(섹션 존재)였고 실행가능성/피드백 충족이 아니었음.
- 수정(소스 = 전 대상자 적용):
  * prompts/dept/planning/concept_planning.md — 플레이스홀더 가드, 아이디어<->캘린더 한 계획,
    해시태그 예시문구 복사금지, 촬영=실제환경 기반, 추천형/어그로 금지 강화
  * prompts/ceo/final_report.md — 이름 정확/축약금지, KPI 현실앵커(300/500)+장기목표 분리,
    로드맵=캘린더 요약
  * agents/ceo.py — _synthesize_final_report 이름 게이트+1회 재시도, payload에 방향 주입,
    _judge_quality 미리보기 500->3000
  * validators/output_validator.py — 컨셉기획 "정보 없음" 누출 가드 + 회귀 테스트 3개
  * docs/실전적용/실행가능성_루브릭.md — 신설(5영역: 정확성/일관성/개인화/피드백/실행가능성)
- 검증(실 gpt-4o, --reanalyze 예으니): 결함 4종 해소. 이름 일관, 플레이스홀더 0,
  KPI 팔로워300/콘텐츠12/조회수[추정]/장기목표1만(방향기반), 아이디어5->캘린더->로드맵 일치.
  잔여(깊이 폴리시, 비차단): 촬영팁 일반론("창가 자연광"+[추정]), 캡션/해시태그 깊이 보통,
  캘린더 5개 반복. 다른 대상자(김하늘 등)는 소스만 고쳐짐(미재생성).
- 다음: docs/실전적용/컨시어지_운영키트.md(운영 런북) -> 실제 미용사 섭외 시 즉시 시작 가능.

### 세션 36 산출 문서
- ADR 032(실사용자 실행가능성 + 생성기 수정), docs/review/2026-06-14-세션36.md,
  docs/실전적용/실행가능성_루브릭.md, 본 status 갱신.

## 세션 36 후속 — 사용자 여정 평가 + 운영 레이어 (16/20 PASS, 확정)
"AI 기준 완료 != 실사용 가능"을 점수로 검증. tests/e2e_user_journey.py 신설:
LLM이 대상자 본인을 연기하며 10단계(계정~성과조정)를 0/1/2 채점 + 결정론적 체크(이름/
플레이스홀더/영어/해시태그/구성).
- 1차(예으니): 13/20 FAIL. 막힘=피드백반영(9)/차주조정(10)=0. 콘텐츠 제작 길(1~7)은 되나
  "한 달 운영/조정 루프"가 사용자 문서에 없었음(운영키트는 운영자용이라 미용사 손에 없음).
- 보완(소스): final_report에 매주 반복 루틴/성과 기록/2주 후 셀프 점검 3섹션 + 영상 아이디어
  구성(훅/핵심/마무리) + 해시태그 최소개수(니치5/트렌드3/대형2) + 4워커 영어번역제약 +
  편집 3단계 + 최종리포트 생성모델 groq->gpt-4o 전환. ceo 최종리포트 게이트에 3섹션 추가.
- 2차(예으니 재생성): 16/20 PASS. 막힌 단계 0, 결정론적 전부 통과(영어 사라짐).
  잔여(1점=멈칫, 비차단): 편집 깊이, 캘린더 "변주" 개념, 분석 숫자 해석.
- 레이트리밋 주의: 세션 호출량으로 OpenAI/Groq throttle, 재생성 수 회 폴백(직전본 복구로 대응).
- 다음: 잔여 3종 보완 / 2번째 대상자로 평가 재현 / UI에 사용자 체크리스트 노출 /
  영어 upstream(01~03 분석) 정리 / 최종리포트 gpt-4o 품질 재측정.

## 1장 졸업 (세션 31 확정)
프로젝트 정체 재정의: 현재 시스템은 "자율 에이전트"가 아니라 "잘 만든 워크플로우".
- 워크플로우 MVP: 90/100 졸업. 자율 에이전트 하네스: 35/100(차대 완성, 엔진 미착수).
- 2장 = 맨 API로 도구 호출 루프 직접 구현(도구/루프/피드백/가드레일). Agent SDK 미사용.
- 선결: 트랙 0(CEO 판단 검증) 필수 승격.
- 문서: docs/1장_졸업선언.md, docs/workflow/2장_에이전트하네스/, ADR 029.

## 현재 세션 포커스 (세션 35 마감 — 인계)
2장 Phase A·C 구현 + 웹 실E2E 검증 + 컨셉출력 심화. 370 pass (343->370).
- Phase A (디렉티브 seam): core/directive.py AgentDirective. CEO plan의 per-agent 지시가
  워커까지 도달(고아 해소) + 깨지기쉬운 ceo_summary 단일깔때기 구조화. build_context가
  per-agent directive를 ceo_summary 키로 주입. stale 코드 정리(_inject_summaries no-op 제거).
  test_directive 8.
- Phase C (도구 호출 루프 — 시스템 최초 '에이전트'): call_llm_tools(프리미티브, ADR029 'tools없음'
  해소) + core/tools.py(WORKER_TOOLS+ToolExecutor, run_partial 재사용) + core/agent_loop.py
  (루프+max_iter 가드레일) + prompts/ceo/autonomous.md + CEO.run_autonomous. 단위 12 +
  통합(실 gpt-4o): 모델이 스스로 도구순서 결정(대상->경쟁->플랫폼->컨셉->finish), 4워커 실행,
  정상정지(5 iter), 산출물4+리포트. 선형 run()은 폴백 유지(병존).
- 웹 실E2E(preview 브라우저, 실 gpt-4o, 김하늘): 인터뷰 7필드 1턴추출 -> 분석 SSE라이브 ->
  관리대시보드(KPI+4주캘린더+산출물4+최종리포트+매니저알림) -> 산출물 열람. 콘솔 에러 0.
- 컨셉출력 심화(실사용자 예으니 피드백 기반): 근본원인=OUTPUT FORMAT이 천장(해시태그1줄/캡션1개/
  편집1줄)이라 재분석2번도 구조 못바꿈. 수정: 해시태그 3층+이유, '### 영상 편집 컨셉' 신설
  (훅/전개/자막/컷), 캡션 2개+, 날조·소재지시 금지 CONSTRAINT. 예으니 실피드백 재생성 5/5 PASS.
  OutputValidator(섹션 필수)+픽스처 갱신.
- 초반: 취준 요약문서(docs/취준_프로젝트요약.md, 코워크 인계판) + 재분석게이트(입력없으면 400 차단)
  + 네비게이션(기존대상자 열람 openSubject) + L3 검증미통과 배지. 설계 재감사(5갭)->04_리팩토링설계.md.

### 다음 세션 시작점 (핑구가 방향 선택)
1. 같은 출력심화를 다른 워커로 — 플랫폼추천/경쟁분석 출력도 얕을 수 있음(예으니류 점검).
2. 웹을 자율루프로 — CEO.run_autonomous를 session_manager/웹에 연결(현재 웹은 선형 run()).
3. Phase B 멀티스텝 재활성화(컨셉 등) — audit G2, 더 깊은 출력. 실 LLM A/B 측정.
4. 컨시어지 1회 — 실제 미용사 정보로 풀 E2E -> 핑구가 산출물 품질 도장 -> 4주 운영.
5. (정합) knowledge 출력형식.md를 새 컨셉 FORMAT에 맞춤(현재 프롬프트가 이김, cosmetic).
6. (파킹) 워크플로우 vs 에이전트 A/B 비교 — 2장 로드맵 E단계.

### 잔존물 (핑구 확인 후 처리)
- src/_e2e_agent_loop_result.txt — Phase C 통합결과 보존, 확인 후 삭제.
- src/outputs/{김하늘,예으니,자율통합_가상미용사} — 세션35 테스트 산출물. 예으니는 실사용 데이터
  (실 피드백 포함) 보존 권장. 나머지 데모는 확인 후 삭제 가능.
- .claude/launch.json 'influencer-agent-ui'(포트8001) — preview/수동 기동용, 유지.
- 커밋 없음(git 미지시).

### 세션 35 산출 문서
- ADR 031(Phase A 디렉티브 + Phase C 도구루프), docs/review/2026-06-14-세션35.md,
  04_리팩토링설계.md(Phase A·C 완료 반영), docs/취준_프로젝트요약.md, 본 status 갱신.

## 세션 34 마감 (히스토리)
세션 32~34 누적: 1장 웹을 실사용 가능 수준으로 하드닝 완료. 343 pass.
- 웹 복구 버그 5건(Fix A~E) + CEO 완료메시지 연동 + 피드백 실반영(통합 100/100).
- 방향 설정(인터뷰 선택지+채팅 포착->방향.md->ceo_summary->에이전트 반영) + 실제 CEO 채팅 백엔드.
- 측정 레이어(core/measure.py: KPI/변수태깅/의사결정 provenance AI|사람) + 매니저 도크 입력 UI.
- 견고성: 폴백 가시화(judgment_fallback emit 7곳), 채팅 jsonl 영속+복원, 캐시버스팅(?v=부팅토큰),
  테스트 위생(outputs 무오염), 검증기 반복체크 실측 보정(윈도우8/임계10).

### 다음 세션 시작점 (우선순위 순)
1. 핑구 직접 웹 E2E (예정 동선: 인터뷰[방향질문] -> 분석 -> 채팅[방향배너->저장하고 재분석]
   -> 새로고침 복원 -> 매니저탭 측정기록(KPI/게시물 태깅) -> 피드백 '전달하고 재분석' -> 재실행 배너)
   -> 발견 버그 수정.
2. 컨시어지 온보딩: 실제 미용사 정보 수집(핑구, 임계경로) -> 1차 분석 -> 전략요약+주간카드 전달
   -> 4주 운영 시계 시작 (Week별 측정 기록은 매니저 도크 '측정 기록' 사용).
3. T(최소 자율 루프): 운영 Week1 병행 빌드 (2장 로드맵). 트랙0 잔여는 T에 흡수.
4. (파킹, 나중에) 워크플로우 vs 에이전트 비교 실험 — 2장 로드맵 E단계 참조. T 완료 후 셋업.

### 잔존물 (핑구 확인 후 처리)
- src/_e2e_direction_result.txt / _e2e_ceo_summary.txt / _e2e_ceo_full.txt — 결과 보존 중, 확인 후 삭제.
- outputs/ 비어 있음(기존 산출물은 세션 33에서 핑구 지시로 전체 삭제 — 새로 만들 예정).
- 커밋 없음(git 작업 미지시) — 필요 시 핑구 지시로.

### 세션 34 산출 문서
- ADR 030(측정 레이어+하드닝), docs/review/2026-06-11-세션34.md, 본 status 갱신.

## 세션 32 진행 — 웹 복구 버그 Fix A + Fix B 완료 (브라우저 E2E 검증)
- Fix A (복구): main.js 인메모리 부팅복구 -> actions.js bootRecover() 디스크 우선 전환.
  influencerName으로 /api/reports + /api/plan 먼저 복원(ceoState=completed). 404여도 reset 금지.
  죽은 job은 catch에서 currentJobId=null + localStorage ceo_job_id 제거(이름 폴백 활성화).
- Fix B (상세보기): ceo.py /agent-output/{job_id} 가 job 없으면 첫 세그먼트를 이름으로 간주해
  디스크 raw_output.md 폴백. views.js agentTile 상세버튼 currentJobId||influencerName +
  완료상태 노출(ref encodeURIComponent).
- 검증: 268 pass 무회귀, CJK 0, node --check 3파일 OK. preview 브라우저: 죽은 job 재시작
  시나리오에서 박민지 완료 대시보드 복원(reports 5/plan weeks 4), 경쟁분석 상세 935자 디스크 로드,
  콘솔 에러 0.
- 남음: Fix D(피드백 흐름) -> E(교정 루프) -> C(CEO 채팅). 아래 원본 계획 유지.

## 세션 32 후속 — Fix D + E + C 완료 (웹 복구 버그 5건 전부 마감)
- Fix D (피드백 흐름 정직화): 매니저 도크 '매니저에게 전달'(가짜 ack, 재분석 미트리거)
  -> '전달하고 재분석 ->' + Actions.deliverToManager(). 저장 경로를 startReanalyze(name)로
  단일화(성과·피드백 저장 후 실제 재분석 트리거). startReanalyze는 성공 bool 반환.
- Fix E (교정 루프): ceo.py _decide_rerun이 reason을 print만 하던 것 -> 모든 경로에서
  self._last_rerun_reason 저장 + run_reanalyze가 'rerun_decided'(rerun_agents+reason) emit.
  프론트: model.rerunDecision, pushActivity가 이벤트 수신, viewRerunBanner가 작업영역 상단에
  '재실행: <에이전트> / <사유>' 표시 + '교정하고 다시 ->'가 매니저 입력 도크를 열어 재전달 루프 완성.
  config TYPE_LABEL rerun_decided, style.css .rerun-banner 추가.
- Fix C (CEO 채팅 정직화): 스텁 채팅의 '실시간 대화 상시' 라벨 -> '준비 중, 성과·피드백은
  매니저 정보 탭 이용' 정직 안내 + placeholder 수정. 백엔드 채팅 엔드포인트는 별도 범위(deferred).
- 검증: 268 pass 무회귀, CJK 0, node --check 4파일 OK, ceo.py import OK.
  preview 브라우저: rerun_decided 주입 -> 배너 렌더(컨셉기획·경쟁분석+사유), 백엔드->프론트 키매핑,
  '교정하고 다시'->매니저 도크 전환, deliver 버튼 배선, Fix C 라벨 확인, 콘솔 에러 0.
  백엔드: _decide_rerun no-feedback 경로 reason 저장(22자)+4개 반환, run_reanalyze emit 배선 확인.
- 남은 deferred: 사용자<->매니저 멀티턴 대화 -> 매니저가 CEO 보고 / 실제 CEO 채팅 백엔드.

## 세션 34 완료 — 측정 레이어(P1) + 견고성(P2) 전부 마감 (핑구 E2E 대기)
- P1 측정 레이어(TDD 19개): core/measure.py — WeeklyKPI/ContentEntry(변수태깅:
  주제/형식/길이/시간대)/DecisionEntry(provenance AI|사람 필수). MeasureStore가
  .system/measure/{kpi,content_log,decision_log}.md 마크다운 테이블로 영속,
  compare_by(변수별 평균 조회/참여), weekly_report. 03_측정실험설계 스펙 구현.
- P1 후킹: AI=ceo.run_reanalyze 재실행 결정 자동 로깅 / 사람=PUT /direction 방향변경
  로깅. API routes/measure.py(PUT kpi, POST content, GET summary). 매니저 도크에
  접이식 '측정 기록' UI(KPI 미니폼+게시물 태깅폼) — 브라우저 E2E: 저장->집계 확인.
- P2 견고성: (a)테스트 위생 — test_reanalyze_api에 김민수 cleanup fixture, 스위트 후
  outputs/ 무오염 확인. (b)Track0 폴백 가시화 — CEO 판단 7곳 except에 _emit_fallback
  ('judgment_fallback' 이벤트, TYPE_LABEL '판단 폴백'). 폴백은 유지하되 관찰가능.
  (c)채팅 영속 — chat_history.jsonl(fm append/load) + ChatEngine 생성시 복원 +
  GET /chat/history + bootRecover 복원. 브라우저: 전송->새로고침->3턴 복원 확인.
  (d)재분석 입력 로딩 _load_reanalyze_inputs로 추출(추적 단일지점).
- 검증: 343 pass (313->343, 신규 30: measure14+hooks5+fallback4+persist7), CJK 0,
  콘솔 에러 0, outputs 클린.
- 다음: 핑구 직접 웹 E2E -> 컨시어지 온보딩(실제 미용사 정보 = 임계경로).
  보류: T(최소 자율 루프)는 운영 Week1 병행(로드맵).

## 세션 34 진행 — MVP 하드닝 (Phase 1 풀E2E + Phase 4 캐시버스팅)
계획: 1)풀 E2E 드라이런 2)Track0 폴백 가시화 3)측정레이어 4)견고성(캐시/채팅영속/위생).
- Phase 1 풀 E2E(e2e_ceo_quality, 실 LLM): CEO.run() 완주, 폴백 0건(판단 6개 전부 실제
  LLM 발화 - Track0 V-1 양호), 12 LLM콜, 산출물4+매니저+plan전략보존 정상.
  발견·수정(이음새 버그): 컨셉기획이 OutputValidator 반복체크에 걸려 검증 실패 ->
  원인은 4글자 n-gram 반복임계(20)가 미용사 도메인단어 '스타일링'x35를 복붙으로 오판.
  수정: 윈도우 4->8, 임계 20->10(_NGRAM_WINDOW/THRESHOLD). 보정근거: 정상출력 윈도우8
  최대 4회 vs 복붙 12회+ -> 깔끔히 분리. 도메인단어 통과, 복붙은 여전히 탐지.
  test_output_validator +3(도메인단어 미플래그/복붙 플래그/정상). 313 pass.
- Phase 4a 캐시버스팅: api/main.py GET '/' 라우트가 index.html의 로컬 자산(js/css)에
  부팅토큰 ?v= 주입(StaticFiles 마운트 앞). 서버 재시작=코드변경 시 브라우저 자동 refetch.
  CDN(https) 제외. 스모크: / 가 ?v=토큰 주입 HTML 반환, 자산 200. -> 핑구 E2E 시
  강력새로고침 불필요(이전 api.js 캐시 혼란 해소).
- 남은 Phase: 2)Track0 런타임 폴백 emit 3)core/measure.py 4b)CEO채팅 디스크영속 +
  재분석입력 로딩 DRY + 테스트위생(outputs 오염 cleanup fixture).

## 세션 33 통합검증 — 방향 반영 강화 (65 -> 100/100)
- 통합테스트(tests/e2e_direction_chat.py, 실 LLM + 방향 유/무 대조군) 1차: 65/100.
  배관(채팅 포착->방향.md->ceo_summary 주입)은 PASS이나, 에이전트 산출물 반영 FAIL:
  방향 유/무 컨셉 출력이 거의 동일, '프로필 꾸미기'는 완전 누락. '도달 != 준수' 확인.
- 원인: (1) 4개 프롬프트가 키를 ceo_summary로 잘못 적고 '참고'로 약하게 취급
  (실제 페이로드 키는 ceo_전략_지시). (2) 최우선 제약 지시 부재 -> LLM이 배경으로만 봄.
- 수정: 4개 프롬프트(dept/planning/*)의 '참고: ceo_summary' 줄을 ceo_전략_지시 기반
  '[최우선 제약]' 블록으로 교체. [사용자가 정한 방향]/[사용자 피드백]을 최우선으로 따르고
  산출물을 그 방향에 맞춰 조정, 충돌 시 사용자 방향 우선 명시. (helper write_text, CJK 0)
- 재측정: 100/100. 대조군 with=['연습'] vs without=[] (방향이 출력을 실제 변경).
  핵심 증거: 이전 완전누락이던 '인스타 프로필 꾸미기'가 캘린더 항목으로 등장(진짜 반영).
- 무회귀: 310 pass(프롬프트 FORMAT 헤더 불변 -> OutputValidator 영향 없음). 결과파일
  src/_e2e_direction_result.txt 보존(핑구 확인 후 삭제).

## 세션 33 마무리 — U3 인터뷰 방향 + U6 프론트 연결 (전체 6유닛 완료)
- U3 인터뷰 방향단계: interview_engine _DIRECTION_FIELDS(콘텐츠방향/핵심목표/중점전략)
  extracted 에 포함(get_subject 로는 분리), get_direction()->DirectionProfile.
  prompts/ceo/interview.md 에 선택지 제안형 방향 질문 + 추출필드 추가.
  interview 라우트 confirm 시 _save_direction_if_any -> 방향.md 저장(1차 분석부터 반영). test 6.
- U6 프론트 연결: model chatId/pendingDirection, api chatStart/chatReply/get|saveDirection,
  actions.sendCeoMessage 실연결(스텁 제거) + applyDirection(저장/재분석), reset/신규/재분석시 세션리셋.
  views 채팅 도크 방향포착 배너(저장 + 저장하고재분석) + 정직 문구, style .dir-capture.
- 검증: 310 pass (304->310, 신규 interview_direction 6). CJK 0. node --check 5파일 OK.
  브라우저 스모크(실 LLM): 채팅 왕복 응답, 방향 발화->LLM 포착->배너/버튼->방향.md 저장 확인, 콘솔 0.
  (api.js 는 preview 브라우저 캐시로 인메모리 패치 후 검증 - 디스크/서버/문법 정상.)
- 전체 흐름 완성: 인터뷰/채팅에서 방향 수집 -> 방향.md -> ceo._load_direction -> ceo_summary
  -> 에이전트 프롬프트 반영(피드백과 동일 경로). 6유닛(U1~U6) 전부 완료.
- 발견(별도 작업 플래그): test_reanalyze_api/test_interview_engine 가 outputs/김민수,예은 를
  cleanup 없이 생성 -> 매 테스트런 잔재. teardown fixture 필요(기존 무관, task 분리).

## 세션 33 진행 — 방향 설정 + CEO 채팅 백엔드 (TDD, 유닛 분할)
목표: (1) 사용자가 전략 '방향'을 정하고 (2) 실제 CEO 채팅 백엔드 제작.
설계: 방향=구조화된 피드백 -> 방금 고친 ceo_summary 주입 경로 재사용(DRY). 채팅=방향을
대화로 정하는 자리. SRP/DIP/OCP 고려, 기능 단위별 TDD.
- U1 방향 모델+영속: core/direction.py(DirectionProfile: 콘텐츠/목표/중점전략/메모,
  to/from_markdown, to_prompt_text), file_manager save/load_direction. test 9.
- U2 전략 주입: ceo._load_direction(run/run_reanalyze 연결) + _build_ceo_summary가
  방향을 LLM 입력 포함 + verbatim 첨부. 에이전트 프롬프트까지 도달. test 4.
- U4 ChatEngine: core/chat_engine.py(컨텍스트 조립=최종리포트/산출물/방향/성과/피드백,
  멀티턴 history, 방향 포착 direction_update, LLM 주입 patch가능), prompts/ceo/chat.md,
  file_manager.load_final_report. test 9.
- U5 채팅 API: api/routes/chat.py(POST /chat/start|reply, 세션 레지스트리, ASCII전용),
  reanalyze.py에 direction GET/PUT, main.py 등록. test 7.
- 검증: 304 pass (297->304, 신규 29: direction13+chat_engine9+chat_api7), CJK 0.
- 남은 유닛: U3 인터뷰 방향단계(선택지 제안) / U6 프론트 연결(채팅 실연결+방향 갱신 버튼).
- 결정: D1 저장+버튼(자동재분석 X), D2 별도 방향.md, D3 인터뷰+채팅 양쪽.

## 세션 32 진행 — Fix D/E/C + CEO 메시지 연동 + 피드백 반영 (핵심 버그)
- Fix D (피드백 흐름 정직화): 매니저 도크 '매니저에게 전달'(가짜 ack) -> '전달하고 재분석 ->'
  + Actions.deliverToManager(). 저장+재분석 트리거를 startReanalyze(name) 단일 경로로 통일.
- Fix E (교정 루프): ceo.py _decide_rerun reason 저장 + run_reanalyze가 'rerun_decided' emit.
  프론트 viewRerunBanner: '재실행: <에이전트> / <사유>' + '교정하고 다시 ->'로 매니저 도크 열기.
- Fix C (채팅 정직화): '실시간 대화 상시' -> '준비 중, 매니저 정보 탭 이용' 안내.
- CEO 완료 메시지 연동: 재분석에도 '1차 분석을 마쳤어요' 뜨던 버그 -> session_manager 재분석
  job_completed에 mode:'reanalyze' 부착, pushActivity가 evt.mode 전달, ceoCompletionMessage()가
  mode+rerunDecision(실제 CEO 사유)로 메시지 구성. 1차/재분석 분기 + 1차 시작 시 플래그 리셋.
- 피드백 반영 (핵심): 재분석 피드백이 재실행 에이전트 산출물에 실제 반영 안 되던 버그.
  원인 = 두 게이트 모두 막힘: (1) _build_ceo_summary가 대상자만 봄 (2) 4개 build_prompt가
  get_context_keys()만 직렬화 -> ceo_summary 완전 죽은 경로. 수정: _build_ceo_summary가 피드백/성과를
  LLM 입력에 포함 + raw 피드백 verbatim 첨부, agent_context 대상분석 read에 ceo_summary 추가,
  base_agent._scoped_payload 헬퍼(ceo_전략_지시 주입), 4개 build_prompt가 헬퍼 사용.
- 검증: 275 pass (268+신규 test_feedback_reflection 7), CJK 0, 브라우저 E2E(완료 메시지 분기).
- 잔여(미수정): 사용자<->매니저 멀티턴 대화 / 실제 CEO 채팅 백엔드(deferred).

## 다음 세션 할 일 — 웹 복구 버그 (세션 31 라이브 테스트 발견)
증상: (1) 새로고침/서버 재실행하면 이전 결과 안 나오고 처음부터 (2) 에이전트별 산출물 미표시
     (3) CEO 채팅 실시간 연동 안됨.
근본 원인: 복구·상세조회가 인메모리 job(/api/status/{job_id})에 의존 -> 서버 재시작 시 404 ->
  main.js가 Actions.reset()으로 localStorage+상태 전부 삭제. 데이터는 디스크에 멀쩡함.
  (재분석이 되는 이유: 디스크의 outputs -> 새 라이브 job으로 우회. 죽은 메모리 job을 안 거침.)
- Fix A (핵심, 1·3 해결): main.js 부팅 복구를 디스크 기반으로 전환.
  influencerName으로 /api/reports/{이름} + /api/plan/{이름} 먼저 시도 -> 산출물 있으면
  ceoState='completed'로 완료 대시보드 복원. 404여도 Actions.reset() 금지(디스크 우선).
  메모리 job은 '진행중이면 SSE 재연결' 용도로만.
- Fix B (1 상세보기): /api/agent-output 이 job_id 대신 대상자 이름으로도 raw_output 읽게,
  또는 상세보기를 /reports 산출물(01~04)로 대체. 죽은 job이어도 열리게.
- Fix C (2, 별도): POST /api/chat/{job_id} 구현 또는 'CEO 실시간 대화' 라벨 정직화/비활성.
- Fix D: 매니저 피드백 흐름 정리.
  진단: 재분석은 피드백을 실제 소비함(ceo.run_reanalyze -> _decide_rerun이 LLM으로 재실행 대상 판단).
  문제는 (a) 매니저 도크 '매니저에게 전달' 버튼이 savePerformance/saveFeedback로 디스크 저장만 하고
  가짜 CEO ack만 띄움 -> 재분석을 트리거 안 함 -> 사용자는 '전달했는데 반영 안됨'으로 느낌.
  (b) 피드백/성과 저장이 매니저 도크 + 재분석 화면 양쪽 중복 -> 혼란('재분석에 저장 왜 있냐').
  -> 저장 경로 단일화 + '전달'이 실제로 무엇을 하는지 정직하게(저장만이면 라벨 수정, 또는 재분석 연결).
- Fix E: 피드백 교정 루프(핵심 누락). CEO의 _decide_rerun 결정(어떤 에이전트 왜 재실행)이
  콘솔에만 찍히고 웹 UI에 안 보임. 사용자가 '그 결정 틀렸다 -> 이렇게 교정'하고 재재분석하는
  흐름이 없음. (메커니즘상 피드백 갱신 후 재실행하면 동작하나, 결정 검토·교정 UX 부재.)
  -> 재분석 결과에 'CEO가 X를 Y 때문에 재실행' 표시 + '교정하고 다시' 버튼.
- 다음 범위(이번/다음 세션 아님, 명시 deferred): 사용자<->매니저 대화 -> 매니저가 CEO에 보고
  (멀티턴 매니저 에이전트). 핑구 확정: 별도 범위로 미룸.
우선순위: A(복구) -> D(피드백 흐름) -> E(교정 루프) -> B(상세보기) -> C(CEO 채팅).
관련 파일: api/static/{main.js,actions.js,views.js}, api/routes/{ceo.py,reanalyze.py,reports.py}, agents/ceo.py.


---

## 세션 25 요약

### 완료 작업
1. **Provider fallback 구현** — llm_client.py에 FALLBACK_MAP 추가, 429/503 발생 시 Groq 자동 전환 (1회), 테스트 3개 추가
2. **Validator 수정** — `_check_incomplete_sentences`에서 `근거:`/`출처:` 포함 줄 스킵 (multi-step 포맷 false positive 수정)
3. **E2E 테스트 수정** — `_run_one_agent` monkey-patch 제거 (PlanningDepartment 위임 구조 반영)
4. **무료 tier 한계 확인** — Gemini 503/429, Groq RPM 초과, Groq 413 payload 순차적 실패
5. **multi-step 비활성화** — subject_analyst, competition_analyst, concept_planner `get_steps()→[]` (Groq RPM 이슈)
6. **소크라테스식 근본 원인 분석** — 유료 API 전환 계획 수립 완료

### 근본 원인 분석 결과
| 시도 | 실패 원인 |
|------|---------|
| Gemini 2.5 Flash 무료 | RPM 10건/분 → 503/429 |
| Groq + multi-step | RPM 초과 (에이전트당 4호출) → 429 |
| Groq + single-call | knowledge 66KB > 32K context → 413 Payload Too Large |
| **결론** | 무료 tier로는 knowledge + multi-step 품질 구조 유지 불가. 유료 API 전환 필수 |

### 미완료 (이월 → 세션 26)
- 유료 API 키 세팅 + provider 전환
- E2E 실행 + 품질 측정 (목표 80+)
- P0-3: 성과기록 구조
- P0-4: 재분석 모드 (--reanalyze)
- MVP 완료 선언

### 테스트 결과 (세션 25)
- 단위 테스트: 117/118 pass (1 pre-existing: timestamp collision)
- E2E: provider 이슈로 미완료

---

## Step 진행 현황

| Step | 이름 | 상태 | 위치 |
|------|------|------|------|
| 0 | 문제정의 | 완료 | docs/workflow/step0_문제정의/ |
| 1 | 성공기준 | 완료 | docs/workflow/step1_성공기준/ |
| 2 | 사용자플로우 | 완료 | docs/workflow/step2_사용자플로우/ |
| 3 | MVP범위 | 완료 | docs/workflow/step3_MVP범위/ |
| 4 | 기능명세 | 완료 | docs/workflow/step4_기능명세/ |
| 5 | 기술결정 | 완료 | docs/workflow/step5_기술결정/ |
| 6 | 아키텍처 | 완료 | docs/workflow/step6_아키텍처/ |
| 7 | 구현 | 진행중 | docs/workflow/step7_구현/ |
| 8 | 루프 | 진행중 (Loop-001) | docs/workflow/loops/loop_001_v2-자율에이전트.md |
| 9 | 배포 | 대기 | docs/workflow/step9_배포/ |

---

## Spiral 진행 현황 (Step 7 내부)

| Spiral | 내용 | 상태 |
|--------|------|------|
| 0-A | CEO 뼈대 + 프롬프트 파일 출력 + 핑구 직접 테스트 | 완료 (세션 11~12) |
| 0-B | CEO + Groq API 연결 + 마크다운 저장 | 완료 (세션 13) |
| 0-C | OOP 리팩토링 (SRP/LSP/DIP/OCP) | 완료 (세션 14) |
| 0-D | Registry 리팩토링 (SSoT 7->2) + CJK 감지 + 설계 문서 동기화 | 완료 (세션 16) |
| 0-E | CEO 도메인 지식 18개 파일 + KNOWLEDGE_MAP 수정 | 완료 (세션 17) |
| 1 | 프롬프트 강화 + Department Layer + 하네스 엔지니어링 + 품질 검증 | 완료 (세션 18-19) |
| 2 | 품질 레이어 (Gemini 전환 + _judge_quality + 검색 전략 + UI 수정) | 완료 (세션 22) |
| 3 | 웹 UI (FastAPI + SSE) — 백엔드 | 완료 (세션 20) |
| 3+ | 웹 UI — Claude Design 프론트 통합 + boot recovery | 완료 (세션 21) |
| 4-A | 컨텍스트 복원 + Knowledge 강화 + 에이전트 multi-step 분할 | 완료 (세션 24) |
| 4-B | Provider fallback 완료 + 유료 API 전환 대기 | 완료 (세션 25) |
| 5-A | AgentOutput + AgentContext 기반 구조 | 완료 (세션 27) |
| 5-B | 프롬프트 역할 가이드 + CEO 질문처리 | 완료 (B1~B4) |
| 5-C | 대화형 인터뷰 엔진 | 완료 (세션 27) |
| 5-D | 매니저 + 루프 완성 | 완료 (세션 27) |
| 5-E | 웹 통합 | 대기 |

---

## 다음 세션 시작점

### 세션 27 시작 프롬프트

1. CLAUDE.md session_start 순서대로 읽기
2. docs/workflow/status.md 읽기
3. docs/refs/V2_설계문서.md 읽기 (V2 확장 전체 결정사항 핸드오버)
4. docs/workflow/loops/loop_001_v2-자율에이전트.md 읽기 (Loop 상태)

**Phase 1: Step 6 아키텍처 업데이트**
   a. docs/workflow/step6_아키텍처/아키텍처.md에 V2 레이어 반영
   b. AgentOutput, AgentContext, InterviewEngine, ManagerAgent 위치 확정
   c. 소통 구조도 업데이트

**Phase 2: Spiral 5-A 구현 (AgentOutput + AgentContext)**
   a. AgentOutput dataclass (base_agent.py)
   b. from_raw() lenient 파서 (하위 호환)
   c. agent_context.py — AGENT_SCOPES + build_context()
   d. planning.py — DepartmentResult에 questions/comments 추가
   e. 기존 테스트 수정 (.content 접근)
   f. 단위 테스트 통과 확인

**Phase 3: Spiral 5-B 프롬프트 전환 (시간 여유 시)**
   a. 4개 에이전트 프롬프트 역할 가이드로 재작성
   b. knowledge/에 예시, 출력형식 파일 추가
   c. OutputValidator 테스트 통과 확인

### V2 구현 Spiral 계획
| Spiral | 내용 | 핵심 파일 | 완료 기준 |
|--------|------|----------|----------|
| 5-A | AgentOutput + AgentContext 기반 | base_agent.py, agent_context.py, planning.py | 4개 에이전트 AgentOutput 반환 + 접근권한 테스트 |
| 5-B | 프롬프트 역할 가이드 + CEO 질문처리 | prompts/ 전체, ceo.py | 프롬프트 전환 + Validator 통과 + 품질 유지 |
| 5-C | 대화형 인터뷰 엔진 | interview_engine.py, main.py | CLI 10턴 대화 → subject dict 추출 |
| 5-D | 매니저 + 루프 완성 | manager.py, ceo.py | 주간카드 + --reanalyze 성공 |
| 5-E | 웹 통합 | api/, 프론트엔드 | 웹 채팅 + 대시보드 동작 |

### V1 이월 항목 (V2 구현 시 통합)
| # | 항목 | V2 통합 방식 |
|---|------|------------|
| P0-2 | 경쟁분석 강화 | Spiral 5-B 프롬프트 전환 시 함께 개선 |
| P0-3 | 성과기록 구조 | Spiral 5-D 매니저 에이전트가 담당 |
| P0-4 | 재분석 모드 | Spiral 5-D CEO 재분석 루프로 구현 |
| E2E | 품질 검증 | Spiral 5-A 완료 후 E2E 재검증 |


## 열린 질문
- [x] GROQ_API_KEY 설정 완료 (세션 11 확인)
- [x] SERPER_API_KEY 발급 + 동작 확인 (세션 18)
- [x] 웹 프레임워크 결정 -> FastAPI + SSE 확정 (ADR 012)
- [x] 테스트 인플루언서 별도 확정 불필요 — CLI 입력으로 테스트 (세션 9 확정)
- [x] CEO 도메인 지식 문서 작성 — knowledge/management/ 18개 파일 완료 (세션 17)
- [x] CLAUDE.md Claude Code 전용 섹션 추가 완료 (세션 8)
- [x] pytest 실행 확인 — 141/142 pass (세션 24)
- [x] ADR 017 작성 — Agent Registry 패턴 (세션 18 완료)
- [x] ADR 018 작성 — LLM 캐싱 + Gemini + Department Layer (세션 19 완료)
- [x] ADR 019 작성 — FastAPI + SSE Web UI (세션 20 완료)
- [x] E2E 전체 PASS — Groq 2회 성공 (세션 19)
- [x] Spiral 1 완료 — 품질 77/100 확인 (세션 19)
- [x] Spiral 3 Web UI 완료 — FastAPI + SSE + Vanilla JS (세션 20)
- [x] Spiral 3+ Claude Design 프론트 통합 완료 (세션 21)
- [x] Spiral 2 품질 레이어 구현 완료 (세션 22)
- [x] Phase A 컨텍스트 복원 완료 (세션 24)
- [x] Phase B Knowledge 7개 파일 생성 완료 (세션 24)
- [x] Phase C 에이전트 multi-step 분할 완료 (세션 24)
- [x] P0-1: 컨셉기획 산출물 확장 (캘린더+가이드+해시태그) — 프롬프트 레벨 완료 (세션 24)
- [ ] Gemini E2E 품질 검증 — Gemini 503 overload → 다음 세션 재시도
- [x] gpt-4o 전체 파이프라인 E2E 품질 80+ 검증 — 4개 산출물 90/85/90/85 PASS (세션 28)
- [x] Provider fallback 구현 — 429/503 모두 FALLBACK_MAP 자동 전환 (세션 25)
- [x] MVP 완료 선언 — 세션 26 현재 상태로 선언 (P0-3/P0-4/E2E 이월 포함)
- [x] P0-2: 경쟁분석 — serper 이중검색(쿼리당 6→3회) + 구독자 결정론적 파서 완료 (세션 28)
- [x] P0-3: 성과 기록 구조 — file_manager 저장/로드 + 매니저 성과요청 (세션 27)
- [x] P0-4: 재분석 모드 — run_reanalyze + --reanalyze + 매니저 진행보고 (세션 27)
- [x] P0-5: 한글 인코딩 수정 — main.py UTF-8 래핑 이미 적용됨 (세션 25 확인)
- [x] V2 설계문서 완료 — docs/refs/V2_설계문서.md (세션 26)
- [x] Step 4 V2 기능명세 3개 완료 — 대화형인터뷰, 에이전트자율성, 매니저에이전트 (세션 26)
- [x] MVP 확장범위 확정 — docs/workflow/step3_MVP범위/MVP확장범위.md (세션 26)
- [x] Step 6 아키텍처 업데이트 (V2 레이어 반영) — 세션 27 (섹션 9 추가)
- [x] Spiral 5-A: AgentOutput + AgentContext 구현 — 세션 27 (테스트 50개)
- [ ] Spiral 5-B: 프롬프트 역할 가이드 전환
- [x] Spiral 5-C: 대화형 인터뷰 엔진 — 세션 27 (InterviewEngine, 단위15 + E2E)
- [x] Spiral 5-D: 매니저 + 재분석 루프 — 세션 27 (ManagerAgent, 단위 12)
- [x] Spiral 5-E: 웹 통합 — 서버세션 인터뷰 API + 채팅 UI + 매니저 알림 패널 (세션 28)
- [ ] 실제 미용사 대상자 확보 + 정보 수집
- [ ] 실전 적용 4주 운영 시작

---

## ADR 목록
- [ADR 001] docs/adr/001-세션1-핵심결정.md
- [ADR 002] docs/adr/002-MVP문서분리.md
- [ADR 003] docs/adr/003-모델교체기준.md
- [ADR 004] docs/adr/004-API할당방식-로드맵.md
- [ADR 005] docs/adr/005-경쟁분석-Serper-웹검색.md
- [ADR 006] docs/adr/006-워크스페이스-폴더구조.md
- [ADR 007] docs/adr/007-기능명세-참조구조.md
- [ADR 008] docs/adr/008-회장보고-핑구작업요청-구조분리.md
- [ADR 009] docs/adr/009-llm-client-provider-라우팅.md
- [ADR 010] docs/adr/010-serper-에이전트-직접-호출.md
- [ADR 011] docs/adr/011-ceo-다음에이전트-llm-판단.md
- [ADR 012] docs/adr/012-fastapi-sse-웹프레임워크.md
- [ADR 013] docs/adr/013-에이전트-파일명-영어-스네이크케이스.md
- [ADR 014] docs/adr/014-src폴더-knowledge선택주입.md
- [ADR 015] docs/adr/015-agent-loop-bugfix-rate-limit-retry.md
- [ADR 016] docs/adr/016-oop-refactoring-ceo-decomposition.md
- [ADR 017] docs/adr/017-agent-registry-패턴.md
- [ADR 018] docs/adr/018-llm-cache-gemini-department.md
- [ADR 019] docs/adr/019-fastapi-sse-web-ui.md
- [ADR 020] docs/adr/020-spiral2-quality-layer.md (세션 22)
- [ADR 021] docs/adr/021-multi-step-agent-knowledge.md (세션 24)
- [ADR 022] docs/adr/022-spiral5e-web-integration.md (세션 28)
- [ADR 025] docs/adr/025-track0-supervisory-verification.md (세션 28)
- [ADR 026] docs/adr/026-strategic-plan-preservation-ceo-hygiene.md (세션 28)
- [ADR 027] docs/adr/027-interview-dialogue-submit-separation.md
- [ADR 028] docs/adr/028-관리중심-전환.md (세션 29) (세션 28)
- [ADR 029] docs/adr/029-1장졸업-2장에이전트하네스전환.md (세션 31)
- [ADR 030] docs/adr/030-측정레이어-하드닝.md (세션 34)
- [ADR 031] docs/adr/031-2장-디렉티브-도구호출루프.md (세션 35)
- [ADR 032] docs/adr/032-실사용자-실행가능성-생성기수정.md (세션 36)
- [ADR 033] docs/adr/033-공개레포-분리-문서동기화.md (세션 37)

## Review 목록
- [2026-05-12] docs/review/2026-05-12-세션1.md
- [2026-05-12] docs/review/2026-05-12-step3-MVP범위.md
- [2026-05-12] docs/review/2026-05-12-세션4.md
- [2026-05-12] docs/review/2026-05-12-세션5.md
- [2026-05-13] docs/review/2026-05-13-세션6.md
- [2026-05-13] docs/review/2026-05-13-세션9.md
- [2026-05-14] docs/review/2026-05-14-세션11.md
- [2026-05-14] docs/review/2026-05-14-세션13.md
- [2026-05-15] docs/review/2026-05-15-세션14.md
- [2026-05-15] docs/review/2026-05-15-세션15.md
- [2026-05-16] docs/review/2026-05-16-세션16.md
- [2026-05-16] docs/review/2026-05-16-세션17.md
- [2026-05-18] docs/review/2026-05-18-세션19.md
- [2026-05-19] docs/review/2026-05-19-세션20.md
- [2026-05-20] docs/review/2026-05-20-세션21.md
- [2026-05-21] docs/review/2026-05-21-세션22.md
- [2026-05-21] docs/review/2026-05-21-세션24.md
- [2026-05-30] docs/review/2026-05-30-세션27.md
- [2026-06-01] docs/review/2026-06-01-세션29.md
- [2026-06-02] docs/review/2026-06-02-세션30.md
- [2026-06-04] docs/review/2026-06-04-세션31.md
- [2026-06-11] docs/review/2026-06-11-세션34.md
- [2026-06-14] docs/review/2026-06-14-세션35.md
- [2026-06-14] docs/review/2026-06-14-세션36.md
- [2026-06-15] docs/review/2026-06-15-세션37.md

---

## 완료된 작업 이력
- 2026-05-31 (세션 28): 인터뷰 대화/제출 분리 리팩토링 (UI 5문제)
  - 원인: 단일 state가 대화진행+종료를 묶어 요약표출=종료로 결합 -> reply 차단(#5)
  - 해결: state 제거, confirmed만 유지. reply는 확정 전까지 항상 받음.
    can_submit()=이름+필수4개(대화와 독립). confirm 미충족시 200+missing(대화유지)
  - min_turns 5->3(#2), 프론트 탭 일원화(#1), confirm 3분기로 분석시작/결과흐름(#3#4)
  - core/interview_engine 전면 + routes/interview + app.js. 인프로세스 스모크 전흐름 PASS
  - 전체 247 pass(242+5). CJK 0. ADR 027
- 2026-05-31 (세션 28): 전략 plan 보존 + CEO 언어위생 (소크라테스 재판단)
  - 버그: _update_plan이 _interpret_goal의 LLM 전략 plan을 체크리스트로 덮어씀
    -> 전략=plan.md(보존), 진행=progress.md(분리). save_progress 추가
  - 발견: CEO LLM출력에 외국어필터 누락(plan.md에 중국어/일본어 혼입) -> _FOREIGN_CHAR_RE 적용
  - goal_interpretation 프롬프트 전략깊이 보강(차별화각도/위험요소/구체지시)
  - E2E 재검증: plan 전략보존 True, CJK=0 JP=0, 폴백0, 242 pass. ADR 026
- 2026-05-30 (세션 28): 트랙 0 — 감독층(CEO/매니저) 검증
  - V-1 폴백 계측 E2E(e2e_ceo_quality.py): CEO.run() 실 LLM 완주, 폴백 0건
    _interpret_goal/_build_ceo_summary 실제 발화 확인. 워커4 완료, 매니저 산출물2
  - V-2 판단 타당성: ceo_summary 구체적/타당. 질문분류 실LLM 검증(test_ceo_questions_live)
  - V-3 매니저 결정론적 정확성: 주차 추출 정확(test_ceo_supervisory 9개)
  - V-4 회장보고 조건 갭 기록: 조건9만 확실 발화, 3/6은 죽은코드 -> 어셋션 고정
  - 발견: CEO 판단 메서드 일부는 라이브경로 미사용(죽은코드). e2e 하네스 stdout UTF-8 수정
  - 전체 242 pass (232+10). 코드변경 없음. ADR 025. 결과파일 src/_e2e_ceo_*.txt 보존
- 2026-05-30 (세션 28): Spiral 5-E 웹 통합 (V2 전체 완료)
  - api/routes/interview.py 신규 — 서버 세션 레지스트리(interview_id->InterviewEngine)
    POST /api/interview/start|reply|confirm. confirm 승인 시 start_job으로 CEO 파이프라인 위임
    한글 리터럴 0 (필드키 core.interview_engine import). tests/test_interview_api.py 6개
  - app.js: 인터뷰 채팅 UI(viewInterview) + 추출패널 + 매니저 알림 패널(viewManagerPanel)
    pushActivity가 manager_notification 가로채 managerNotes 누적. 엔트리 '대화 인터뷰' 탭 기본
    API.interviewStart/Reply/Confirm 추가. style.css 채팅/패널 스타일. node --check 통과
  - 라이브 스모크: uvicorn 기동 → /api/interview/start 실 LLM 응답, 3경로 등록, index 200
  - 전체 232 pass (226+6). CJK 오염 0. ADR 022 작성
- 2026-05-30 (세션 28): 품질 검증 — P0-2 파서 + gpt-4o E2E 품질측정
  - P0-2: competition_analyst.py _parse_subscriber_count 추가 (결정론적: 2.13만/1.5K/3M/12,300명/0.5억)
    _collect_search_results가 검색결과에 _subscriber_parsed 주입 → 프롬프트가 우선 사용, 없으면 [unknown]
    LLM 파싱 의존 제거. test_competition_parsing.py 11개 추가 (CJK 0개)
  - E2E 품질: tests/e2e_quality.py 신규 — 가상 미용사(김서연) 4개 에이전트 순차 + LLM 저지(0-100)
    결과: 대상90 / 경쟁85 / 플랫폼90 / 컨셉85, 4개 전부 validate PASS, 외래문자(CJK/JP/CYR) 0개
    경쟁분석 산출물에 실제 구독자 숫자 노출 확인 (8,900/1,590 등, [unknown] 폴백 정상)
  - 전체 226 pass (217 + 신규 11 - 중복정리). 결과파일 src/_e2e_quality_*.txt 보존(핑구 확인 후 삭제)
- 2026-05-30 (세션 27): Spiral 5-D 매니저 + 루프 완성
  - agents/manager.py 신규 — ManagerAgent(BaseAgent 미상속, AGENT_CLASSES 미등록)
    generate_weekly_card/progress_report + request_performance_input + completion_summary + notify
  - file_manager.save_manager_output (.system/manager/), prompts/manager/notification.md
  - ceo.py 연동: _finalize에 완료요약+1주차카드+성과요청, run_reanalyze에 진행보고
  - EventEmitter manager_notification 이벤트, CLI는 emitter 없이 파일저장+로그 폴백
  - P0-3(성과기록)·P0-4(재분석) 통합 완료. 테스트 test_manager.py 12개 + 전체 217 pass
- 2026-05-30 (세션 27): Spiral 5-C 대화형 인터뷰 (CLI)
  - core/llm_client.call_llm_messages 신규 — 멀티턴 messages 배열, 캐시 미사용, 429/503 폴백
  - core/interview_engine.py 신규 — InterviewEngine(start/reply/confirm/get_subject/save) +
    InterviewResponse. JSON 프로토콜(type/message/extracted_so_far/sufficient), 7+4 필드, min/max turn
  - prompts/ceo/interview.md 신규 — CEO 첫상담 시스템 프롬프트
  - main.py: --interview(기본)/--legacy, run_interview_cli (dry-run은 legacy 폴백)
  - 테스트: test_interview_engine.py 15개 + 전체 205 pass
  - 실 LLM E2E(gpt-4o): 6턴 대화 → 11필드 중 10개 추출(카메라경험만 미언급), subject dict 파이프라인 호환
- 2026-05-30 (세션 27): 버그 2건 수정 + 컨셉 다양성 검증 + 올그린
  - competition_analyst 이중 serper 검색 수정 — build_prompt가 run() 주입결과 재사용
    (쿼리당 6→3회). test_agents 단일호출(call_llm==1) 어셋션 현행화
  - file_manager.save_briefing 타임스탬프 충돌 수정 — 동일 마이크로초 시 _n suffix
  - 전체 190 pass (pre-existing 2건 전부 해소, 처음으로 올그린)
  - B3.5 컨셉 다양성 nudge E2E 검증: 3컨셉이 맞춤솔루션/정보교육/소통으로 분화, 품질 90
- 2026-05-29 (세션 27): 5-B B3.5(질문/confidence 활성화) + B4(CEO 질문처리)
  - B3.5: 4개 프롬프트에 질문·신뢰도 규칙 + 품질 nudge(약점=콘텐츠방향/컨셉 소재다양성/SNS경험 명시)
  - B4: ceo._handle_agent_questions 3단계 분류(STRATEGIC/TACTICAL/DATA) + prompts/ceo/question_handler.md
    _agent_loop에 연결, context['질문_응답'] 저장. 단위테스트 test_ceo_questions.py 5/5
  - E2E 진단: 7필드 입력에선 에이전트가 [추정]으로 임무완료 → questions 미발생, confidence 0.85~0.9
    결론: 질문은 막혔을 때의 안전망. 실질 활성화는 5-C 인터뷰(필드 확장)에서. B4 plumbing은 완성·검증됨
  - 전체 188 pass / 2 pre-existing fail. 결과파일 src/_e2e_*.txt 보존(핑구 확인 후 삭제)
- 2026-05-29 (세션 27): 4개 도메인 프롬프트 역할가이드 전환 + 파이프라인 E2E 통과
  - 경쟁/플랫폼/컨셉 3개 도메인 동일 패턴 롤아웃 (대상분석 검증 후)
    각 도메인: 범용 프레임워크 2개 + 출력형식.md + 예시.md + 역할가이드 프롬프트
    범용 프레임워크 8개: 강점도출/약점극복/직업군별경쟁환경/포지셔닝사례/직업군별플랫폼적합도/
    콘텐츠형식플랫폼매핑/콘텐츠포맷라이브러리/캘린더설계패턴
  - FORMAT 헤더·키워드 전부 보존 (OutputValidator RULES 매칭 유지)
  - 전체 파이프라인 E2E(gpt-4o + serper): 4개 에이전트 all validation pass
    품질 대상분석82/경쟁85/플랫폼90/컨셉85, 경쟁분석 실제채널·구독자 파싱 확인
  - AgentContext 필터링·ceo_summary·AgentOutput(comments/confidence) 통합 동작 확인
  - 결과 파일 보존: src/_e2e_result.txt, src/_e2e_pipeline_result.txt (핑구 확인 후 삭제)
- 2026-05-29 (세션 27): Knowledge 정리 + 대상분석 도메인 작성
  - Phase 0: knowledge taxonomy 재구성 — dept/planning/{에이전트}/{프레임워크,사례,출력}/
    base_agent._load_knowledge glob→rglob(재귀), 기존 9파일 재배치, AGENT_SCOPES knowledge 경로 영문 정합
    knowledge/README.md(컨벤션) 신규, 아키텍처.md 트리 갱신. management/는 정돈됨→유지
  - Phase 1: 대상분석 도메인 — 강점도출_프레임워크.md, 약점극복_패턴.md(범용),
    출력/출력형식.md, 출력/예시.md + subject_analysis.md 프롬프트 역할가이드 전환
    (ROLE/GOAL/THINKING_GUIDE/ACCESS/OUTPUT/CONSTRAINTS, FORMAT 헤더 불변, AgentOutput 블록)
  - 검증(무API): system_prompt 14.4KB 조립 확인, 포맷→OutputValidator 통과, AgentOutput 파싱 OK, 전체 183 pass
  - 미완: E2E 품질검증 — .env에 OPENAI_API_KEY/GROQ_API_KEY 없음(이 환경) → 핑구 키 제공 시 실행
- 2026-05-29 (세션 27): V2 Spiral 5-A 완료 + 5-B B1·B2
  - 5-B B1: planning._run_agent가 build_context로 에이전트별 스코프 전달
    (agent_context._OUTPUT_TO_KEY: 01_대상분석.md→대상_분석 등 in-memory 매핑)
  - 5-B B2: ceo._build_ceo_summary — 대상자 기반 전략요약 context['ceo_summary'] 생성
  - 테스트: AgentContext outputs 매핑 5개 추가, 전체 183 pass / 2 pre-existing fail
  - 4개 에이전트 provider=openai gpt-4o 확인 (B3 E2E 준비됨)
- 2026-05-29 (세션 27): V2 Spiral 5-A 구현 (AgentOutput + AgentContext)
  - Step 6 아키텍처.md V2 반영 (섹션 9: 레이어/AgentOutput/AgentContext/데이터흐름)
  - agents/agent_output.py 신규 — from_raw 관대한 파서 (구분자 블록/평문/깨진JSON 모두 처리)
  - agents/agent_context.py 신규 — AGENT_SCOPES + build_context (read 키 필터)
  - departments/planning.py — _run_agent에서 AgentOutput 파싱, DepartmentResult에 questions/comments/confidence 추가
  - agents/ceo.py — _agent_loop/run_reanalyze에서 구조화 피드백 context 저장
  - 테스트: AgentOutput 13 + AgentContext 8 + 통합 6 + DepartmentResult 갱신 = 신규 27개, 5-A 관련 50개 전부 통과
  - 환경 이슈 수정: src/tests/__init__.py 추가 (site-packages tests 패키지 shadowing 해결)
  - 전체 178 pass / 2 pre-existing fail (timestamp collision flake, 경쟁분석 serper 중복호출=P0-2)
  - CJK 검증 통과 (신규/수정 파일 전부 0개)
- 2026-05-28 (세션 26): MVP V1 완료 선언 + V2 자율 에이전트 확장 설계
  - MVP V1 완료 선언 (P0-3/P0-4/E2E 이월 포함)
  - Loop-001 V2 자율 에이전트 확장 진입 (Step 3 복귀)
  - 핑구 Q&A: 대화형 인터뷰(10턴+), 에이전트 자율성, 매니저 보고, CEO 요약 전달 등 확정
  - Step 3: MVP 확장범위 문서 작성 (F1~F8 IN, 6개 OUT)
  - Step 4: 기능명세 3개 병렬 작성 완료 (대화형인터뷰 21KB, 에이전트자율성 27KB, 매니저에이전트 21KB)
  - V2 설계문서(핸드오버) 작성 — docs/refs/V2_설계문서.md (11KB)
  - CJK 검증 통과 (4개 문서 전부 0개)
- 2026-05-24 (세션 25): Provider fallback + 유료 API 전환 계획
  - Provider fallback: FALLBACK_MAP 429/503 → Groq 자동 전환, 테스트 3개 추가
  - Validator: 근거:/출처: 포함 줄 불완전 문장 판정 제외
  - E2E 테스트: monkey-patch 제거 (PlanningDepartment 위임)
  - 무료 tier 한계 최종 확인: Gemini 503/429, Groq RPM/413 전부 실패
  - multi-step 비활성화 (get_steps→[], Groq RPM 이슈)
  - 유료 API 전환 소크라테스식 계획 수립 완료
- 2026-05-21 (세션 24): Phase A+B+C 구조 개선
  - Phase A: _inject_summaries no-op (3-line 압축 제거), 토큰 확대 (LLM 8000, CEO 1000)
  - Phase B: Knowledge 7개 도메인 지식 파일 (미용사 사례~아이디어뱅크)
  - Phase C: Template Method Pattern — SubjectAnalyst 4-step, CompetitionAnalyst 4-step, ConceptPlanner 5-step
  - Gemini 2.5 Flash 모델 적용 (대상분석+경쟁분석)
  - 테스트: multi-step 테스트 교체, 141/142 pass
  - 소크라테스식 향후 계획 수립
- 2026-05-21 (세션 22): Spiral 2 품질 레이어 구현
  - 프롬프트 4개 강화: SENTENCE QUALITY, BANNED EXPRESSIONS, FORMAT RULES
  - Validator 강화: 불완전 문장, n-gram 반복, 미확인 과다, generic phrases
  - UI 3건 수정: detail 항상 표시, 에이전트 카드뉴스+상세 모달, 결재 캐시 버그
  - 경쟁분석 검색 전략: 3-쿼리 크리에이터 전용 ("유튜버 OR 크리에이터 OR 채널")
  - 생성 모델 Gemini 전환: DEFAULT_PROVIDER="gemini", MODEL="gemini-2.0-flash"
  - _judge_quality: Groq가 Gemini 산출물 0-100 평가, 65점 미만 재시도
  - 테스트: 136 -> 141 (신규 5개 judge), 140/141 pass
- 2026-05-20 (세션 21): Claude Design 프론트엔드 통합 + Backend 보강
  - Backend: EventEmitter 링버퍼 + GET /status 보강 (subject, reports, recent_events)
  - Frontend: Claude Design production 품질 (라이트/파스텔/퍼플, 820줄 app.js)
  - API 어댑터 패턴: 백엔드 API 보존, 프론트에서 매핑
  - Boot Recovery: localStorage + API 재조회 + SSE 재연결
  - 테스트: 121 -> 132 (신규 11개), 131/132 pass
  - 서버 검증: uvicorn 8001, 전 엔드포인트 200 OK
- 2026-05-19 (세션 20): Spiral 3 Web UI 구현
  - EventEmitter: CEO-SSE 디커플링 브릿지 (queue.Queue + append_log)
  - SessionManager: 멀티잡 라이프사이클 (JobContext + threading)
  - API Routes: FastAPI 12개 엔드포인트
  - Frontend: index.html + style.css + app.js (Linear/Vercel 다크 테마)
  - CEO/Department 수정: event_emitter + _emit() + decision gate
  - 테스트: 101 -> 121 pass (API 20개 신규)
  - ADR 019, 세션 20 리뷰 작성
- 2026-05-18 (세션 19): 프롬프트 강화 + Department Layer + 하네스 엔지니어링
  - Department Layer: departments/planning.py (기획본부) 신규
  - 프롬프트: 4개에 [THINKING] + [SELF-CHECK] + [EXAMPLES] 추가
  - 하네스: Generic phrase 감지, Two-pass 컨셉기획, Foreign char regex 확장
  - Foreign char regex: accented Latin + Cyrillic + Arabic + Thai 추가
  - 테스트: 74 -> 101 pass (27개 추가)
  - E2E: Groq 2회 전체 PASS, 품질 60 -> 77/100
  - ADR 018 작성, 세션 19 리뷰 작성
  - MAX_RETRY=1, LLM_MAX_RETRIES=4, LLM_MAX_TOKENS=2500 설정
- 2026-05-16 (세션 18): LLM 최적화 + Gemini 추가 + E2E 인프라
  - 임시 파일 5개 삭제 (outputs/ _write_knowledge_*.py + run_test.py)
  - ADR 017 작성 (Agent Registry 패턴)
  - 세션 16 리뷰 작성
  - 일본어 오염 fix: OutputValidator CJK 범위 확장 + 프롬프트 LANGUAGE CRITICAL
  - 경로 영어화: prompts/dept/planning, knowledge/management, knowledge/dept
  - CEO 최적화: _decide_next/_interpret_goal LLM 제거 (4 calls 고정)
  - LLM 캐싱: core/llm_cache.py MD5 파일캐시
  - Gemini 추가: PROVIDER_CONFIG + BaseAgent provider/model class var
  - E2E 테스트: tests/e2e_gemini.py (Step1+2 PASS 확인)
  - 설정: MAX_RETRY=0, LLM_MAX_RETRIES=1
- 2026-05-16 (세션 17): CEO 도메인 지식 문서 작성
  - knowledge/management/ 9폴더 18개 파일 (개념.md + 프레임워크.md)
  - KNOWLEDGE_MAP에 02_마케팅관리 -> 전략수립 추가
  - CJK 한자 0개 검증
- 2026-05-16 (세션 16): Registry 리팩토링 + 설계 문서 동기화
  - agents/__init__.py 신규 — AGENT_CLASSES Registry SSoT
  - BaseAgent context_key, output_prefix, output_label 클래스 변수 추가
  - CEO AGENT_KEY_MAP 하드코딩 제거
  - OutputValidator CJK 감지 + 섹션 범위 count_check
  - 아키텍처.md 전체 재작성
  - pytest 75/75 pass
