# Project: 인플루언서 에이전트
# AI 기획사 — 에이전트 조직이 인플루언서 전략·기획·분석을 대신한다
# goal: portfolio + production (실제 인플루언서 적용 → 구독자 수 성장 측정)
# 역할 주의: 이 저장소를 만드는 주체는 Claude(개발자)다. CEO·매니저·워커는 모두
# 개발·검증 대상이다. 회장 보고·자율 루프·매니저 알림은 '내가 따르는 규칙'이 아니라
# '내가 구현하고 검증하는 시스템의 명세'다.

## session_start
# 새 세션 시작 시 아래 순서대로 읽어라. 읽기 전 작업 시작 금지.
1. .claude/AIEngineering.md              ← 규칙·트리거 내면화
2. .claude/personalization.md            ← 사용자 프로필
3. .claude/lessons.md                   ← 반복 금지 패턴 (파일 작성·테스트·프로세스 규칙)
4. docs/workflow/status.md               ← 현재 step + 다음 시작점
5. status.md "현재 세션 포커스" 업데이트
6. docs/refs/에이전트_설계원칙.md        ← 에이전트 프롬프트 작성 전 반드시 읽기
7. docs/refs/실전적용_로드맵.md          ← 성공 기준·시스템 확장·4주 계획 (필독)
8. 해당 step 폴더 로드 (docs/workflow/step{N}_{이름}/)

# 필요 시만 지연 로드 (참고용 — 덮어쓰기 금지):
# task_08_인플루언서에이전트/인플루언서에이전트_MVP.md
# task_08_인플루언서에이전트/인플루언서_에이전트_최종목표.md
# task_08_인플루언서에이전트/조직구조_설계.md
# task_08_인플루언서에이전트/워크스페이스_구조.md

## Success
# 원칙: MVP부터 실제 사람에게 적용 — 품질 기준 타협 없음
# 프로젝트 성공 = 실제 미용사 1명에 적용 → 1개월 내 팔로워 300+ (최소) / 500+ (목표)
# MVP 확장: 4개 산출물 + 콘텐츠 캘린더 + 실행 가이드 + 성과 추적 + 재분석 모드
# 상세: docs/refs/실전적용_로드맵.md

## Agent 동작 원칙
- 핑구는 목표·목적만 제시. 나머지는 에이전트가 자율 판단·관리.
- 하위 에이전트는 전체 파일 접근 가능 — 필요한 파일만 스스로 참조
- 경영 에이전트는 읽기 규칙을 시스템 프롬프트에 명시
- 회장 보고: 맨 마지막 X → 주요 결정 변경 감지 시 즉시 보고 (보고 조건 10개 기준)
- 무상태 시작 — 목표·목적 외 사전 입력 없음

## Stack
- Language:  Python 3.11+
- Framework: 없음 (LangChain X — Groq API 직접 호출)
- Model:     생성 = gpt-4o (워커 4개 + CEO 판단 + 인터뷰). 품질저지 = Groq llama-3.3-70b.
#            Gemini = 폴백. (세션 22~28에서 무료 tier 한계로 gpt-4o 전환 확정)
- Search:    Serper API (무료 2,500건/월) — 경쟁 분석 웹 검색용
- DB:        없음 (마크다운 파일 기반)
- UI:        CLI + 웹(FastAPI+SSE) 둘 다 완료 — 인터뷰 채팅·CEO 자율루프·매니저 패널·재분석
- Build:     없음

## Commands
# 모든 명령은 src/ 디렉터리 기준 (ADR 014 — 런타임 레이어 격리)
- install:   `pip install requests python-dotenv fastapi uvicorn`
- run:       `cd src && python main.py`               ← 기본: 대화형 인터뷰 모드
- legacy:    `cd src && python main.py --legacy`       ← 기존 7필드 폼 입력
- reanalyze: `cd src && python main.py --reanalyze --name {이름}`  ← 성과기반 재분석
- run dry:   `cd src && python main.py --dry-run`      ← API 없이 프롬프트 파일 출력
- web:       `cd src && python -m uvicorn api.main:app --port 8000`  ← 웹 UI (인터뷰·대시보드)
- test:      `cd src && python -m pytest -q`           ← 전체 테스트 (세션 28: 232 pass)

## Claude Code 전용 (자동 실행 모드)
# Spiral 0-B 이후 Claude Code task 단위 분리 기준 (경로는 src/ 기준)
task_units:
  - src/core/llm_client.py       ← 독립 구현·테스트 가능
  - src/core/serper_client.py    ← 독립 구현·테스트 가능
  - src/core/file_manager.py     ← 독립 구현·테스트 가능
  - src/agents/base_agent.py     ← core/ 완료 후
  - src/agents/subject_analyst.py       ← base_agent 완료 후, 단독 테스트
  - src/agents/competition_analyst.py   ← subject_analyst 완료 후
  - src/agents/platform_recommender.py  ← competition_analyst 완료 후
  - src/agents/concept_planner.py       ← platform_recommender 완료 후
  - src/validators/output_validator.py  ← 에이전트 명세 확정 후 (Step 4 기준)
  - src/agents/ceo.py                   ← 구현 완료. 단 LLM 판단 6개 메서드 품질 미검증(테스트는 mock=배선만)
  - src/agents/manager.py               ← 구현 완료. 산출물 유용성 미평가
  # 검증 공백: 워커 4개는 실 LLM E2E 90/85/90/85 측정됨. CEO/매니저(감독층)는 미측정 → 확장 트랙 0 참조
read_before_impl:
  - docs/workflow/step6_아키텍처/아키텍처.md  ← 구현 기준 문서
  - docs/workflow/step5_기술결정/흐름정리.md  ← 전체 흐름 기준

## Don'ts
- LangChain / 에이전트 프레임워크 사용 금지 (이유: MVP는 구조 검증이 목적 — 추상화 제거)
- 에이전트 전체 합친 후 테스트 금지 (이유: 하나씩 독립 테스트 후 연결)
- 확장은 회장 승인됨 (세션 28) — Loop 단위로 진행. 단 감독층(CEO/매니저) 검증을 확장보다 선결
  (이유: 미검증 지휘층 위에 부서 추가 금지. 상세 → docs/refs/확장_로드맵.md 트랙 0)
- 회장 보고 조건 단독 결정 금지 (이유: 비용·법적·실행 전환은 반드시 핑구 승인)
- 파일 작성·변경 전 내용 요약 → 핑구 승인 후 작성 (이유: 방향 오류 사전 차단)
- task_08 기존 파일 덮어쓰기 금지 (이유: 참고용 — step 폴더에 새로 작성)
- 세션 종료 시 ADR·review 반드시 작성 (이유: 결정사항 누락 방지)
- 한글 포함 파일은 Edit/Write/PowerShell 금지 → Python write_text(encoding="utf-8") 전용 (이유: CJK 코드포인트 혼입, 세부 규칙 → .claude/lessons.md)
- 실행 전 원인 분석 먼저 — 같은 파일 3회 이상 재작성 시 즉시 중단 후 근본 원인 파악
- 사용자 피드백 수신 즉시 기존 파일 전체 검증 후 다음 작업 진행

## Structure
# 빌드 레이어 (Claude Code·인간용) / 런타임 레이어 (에이전트 실행용) 분리 (ADR 014)
```
인플루언서_에이전트/              ← 프로젝트 루트
├── .env                          ← API 키
├── requirements.txt
├── CLAUDE.md                     ← 빌드 레이어
├── docs/                         ← 빌드 레이어 (설계 문서)
│   ├── workflow/
│   │   ├── status.md
│   │   ├── step0_문제정의/
│   │   ├── step1_성공기준/
│   │   ├── step2_사용자플로우/
│   │   ├── step3_MVP범위/
│   │   ├── step4_기능명세/
│   │   │   ├── 기능명세.md
│   │   │   ├── MVP_기능명세.md
│   │   │   ├── 워크스페이스_구조.md   ← outputs/ 폴더 구조 기준
│   │   │   ├── CEO/                   ← CEO 에이전트 설계 (00~08)
│   │   │   └── 하위에이전트/          ← 직무 에이전트 4개 설계
│   │   ├── step5_기술결정/
│   │   ├── step6_아키텍처/
│   │   ├── step7_구현/
│   │   ├── step8_루프/
│   │   └── step9_배포/
│   ├── adr/
│   ├── refs/
│   └── review/
│
└── src/                          ← 런타임 레이어 (에이전트 실행 전용)
    ├── main.py                   ← CLI 진입점 (--interview 기본 / --legacy / --reanalyze / --dry-run)
    ├── core/                     ← 인프라: llm_client, llm_cache, file_manager, config,
    │                                serper_client, state_manager, report_builder,
    │                                prompt_loader, interview_engine, scheduler
    ├── agents/                   ← base_agent, ceo, manager, 워커 4개(subject/competition/
    │                                platform/concept), agent_context, agent_output, __init__(레지스트리)
    ├── departments/              ← 부서 레이어: planning.py (기획본부, 단일 구현)
    ├── validators/               ← output_validator
    ├── api/                      ← 웹 (FastAPI+SSE): main, session_manager, event_emitter,
    │   ├── routes/               ←   ceo, stream, decision, reports, reanalyze, interview
    │   └── static/               ←   index.html, app.js, style.css (인터뷰 채팅·대시보드·매니저 패널)
    ├── prompts/                  ← 시스템 프롬프트 (영문 경로 — ADR 016)
    │   ├── ceo/                  ←   goal_interpretation, next_decision, question_handler, interview
    │   ├── dept/planning/        ←   subject/competition/platform/concept_*.md
    │   └── manager/              ←   notification.md
    ├── knowledge/                ← 판단 근거 지식 (영문 경로 — ADR 016)
    │   ├── management/           ←   CEO 선택 주입 (KNOWLEDGE_MAP, 9개 영역)
    │   └── dept/planning/        ←   워커별 {프레임워크,사례,출력형식} (rglob 재귀 로드)
    └── outputs/                  ← 런타임 산출물 (인플루언서별)
        └── {인플루언서명}/
            ├── 산출물/           ← 핑구가 보는 최종 결과 + .versions/
            ├── 인수인계/
            └── .system/
                ├── ceo/          ← plan.md, state.md, snapshots/
                ├── agents/       ← raw_output, validation, rework, .versions/
                ├── briefings/    ← 회장 보고 이력
                ├── prompts/      ← Spiral 0-A 전용
                └── logs/         ← UI 실시간 표시용 (.jsonl)

task_08_인플루언서에이전트/       ← 참고용 (수정 금지)
```

## Workflow
- status:  @docs/workflow/status.md
- step0:   @docs/workflow/step0_문제정의/
- step1:   @docs/workflow/step1_성공기준/
- step2:   @docs/workflow/step2_사용자플로우/
- step3:   @docs/workflow/step3_MVP범위/
- step4:   @docs/workflow/step4_기능명세/
- step5:   @docs/workflow/step5_기술결정/
- step6:   @docs/workflow/step6_아키텍처/
- step7:   @docs/workflow/step7_구현/
- step8:   @docs/workflow/step8_루프/
- step9:   @docs/workflow/step9_배포/

## References (참고용)
- 프로젝트 비전:  @docs/refs/비전.md                 ← 방향 잃었을 때 여기 (한 파일 요약)
- AI 학습자료:    @docs/refs/AI_학습자료.md          ← LLM·에이전트 기초 개념 (핑구용)
- 에이전트 설계:  @docs/refs/에이전트_설계원칙.md     ← 시스템 프롬프트 작성 기준 (Claude용)
- 조직구조:       @task_08_인플루언서에이전트/조직구조_설계.md
- MVP범위:        @docs/workflow/step3_MVP범위/MVP범위.md
- 최종목표:       @docs/workflow/step3_MVP범위/최종목표.md
- 워크스페이스:   @docs/workflow/step4_기능명세/워크스페이스_구조.md
- 실전 적용:    @docs/refs/실전적용_로드맵.md      ← 성공 기준 + 시스템 확장 + 4주 실행 계획
- 확장 로드맵:  @docs/refs/확장_로드맵.md          ← V2 이후 확장(트랙 0 감독층검증 → B/C/A)
- adr:            @docs/adr/
- review:         @docs/review/
