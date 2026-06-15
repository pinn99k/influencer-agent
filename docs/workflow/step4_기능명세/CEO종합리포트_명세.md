# 기능명세 — CEO 종합 리포트 + 실행계획 구조화 (Loop-002 백엔드)
# 대상: 코덱스(Codex) 구현용. 이 문서 + 코드만으로 구현 가능하도록 정밀 기술.
updated: 2026-06-01 (세션 29)

> 원칙: 기존 인프라 유지, 에이전트/리포트 레이어만 보강. 폴백 제거 금지.
> 한글 포함 파일은 반드시 UTF-8. 외래문자(CJK한자/일본어/키릴) 0 유지.

---

## 0. 전체 그림

```
[기존]  워커4 분석 -> _finalize -> build_final_report(이어붙이기) -> 최종리포트.md
[변경]  워커4 분석 -> _finalize -> _synthesize_final_report(LLM 종합) -> 최종리포트.md
                                    +- 실패 시 build_final_report 폴백(유지)
[신규]  04_컨셉기획.md + 최종리포트.md -> plan_extractor -> GET /api/plan/{name}
                                                          -> 프론트 State.plan
```

작업은 3덩어리: B1(LLM 종합 리포트), B2(plan 파서+API), F2(프론트 컨트롤러 배선).
뷰(views.js/style.css)는 본 문서 범위 아님 -> 핸드오프_v4 + Claude Design 담당.

---

## B1. CEO 종합 리포트 (LLM 종합)

### B1-1. 신규 프롬프트 파일
경로: src/prompts/ceo/final_report.md  (영문 경로 규칙 — ADR 016)
역할: 4개 분석 + 캘린더를 입력받아 "의사결정 가능한 종합 보고서"를 쓴다.
반드시 아래 6개 섹션 헤더를 정확히 출력 (plan_extractor 와의 계약):

```
# {이름} 인플루언서 전략 보고서

## 한 줄 결론
{어떤 플랫폼에서 어떤 컨셉으로 가야 하는가 — 1~2문장}

## 핵심 결정 3가지
1. 플랫폼: {1순위} — {근거 1문장}
2. 컨셉: {선택 컨셉명} — {근거 1문장}
3. 타겟: {타겟} — {근거 1문장}

## 강점과 기회
{대상분석+경쟁분석 종합. 강점 2~3개와 시장 공백 1~2개 연결. generic 금지}

## 4주 실행 로드맵
- Week 1: {핵심 목표 + 콘텐츠 수}
- Week 2: {...}
- Week 3: {...}
- Week 4: {...}

## 지금 당장 할 3가지
1. {오늘~3일 내 실행 가능한 구체 행동}
2. {...}
3. {...}

## 성공 지표 (30일)
- 팔로워: {목표 수치}
- 콘텐츠: {개수}
- 핵심 KPI: {조회수/저장수 등 1개}
```

프롬프트 본문 작성 규칙(파일 안에 명시):
- [ROLE] AI 기획사 CEO. 분석을 종합해 회장(핑구)과 크리에이터가 바로 실행할 보고서를 쓴다.
- [GOAL] 위 6섹션을 모두 채운다. 분석 원문 복붙 금지 — 종합/우선순위/결정.
- [CONSTRAINTS] 한국어만. CJK한자/일본어/키릴 금지. 대상자 이름 포함. 추측은 [추정] 태그.
  4주 로드맵의 각 Week 줄은 반드시 "- Week N:" 으로 시작 (파서 계약).
- 입력은 user 메시지로 JSON 전달 (아래 B1-2).

### B1-2. ceo.py 변경
위치: src/agents/ceo.py — _finalize (현재 352행 부근).

현재 _finalize 는 build_final_report(이어붙이기)를 호출한다. 이를 종합 메서드 경유로 바꾼다:

```python
def _finalize(self, context):
    self._emit("finalize_started")
    self._request_approval(context)
    final_report = self._synthesize_final_report(context)   # NEW
    self.fm.save_final_report(final_report)
    self._notify_manager_completion(context, final_report)
    ...  # 이하 기존 동일 (snapshot, handover)

def _synthesize_final_report(self, context) -> str:
    # LLM이 4개 분석+캘린더를 종합한 전략 보고서. 실패 시 기존 이어붙이기 폴백.
    payload = {
        "대상자": context.get("대상자", {}),
        "대상_분석": context.get("대상_분석", ""),
        "경쟁_분석": context.get("경쟁_분석", ""),
        "플랫폼_추천": context.get("플랫폼_추천", ""),
        "컨셉_기획": context.get("컨셉_기획", ""),
    }
    try:
        system = self._prompts.load_prompt("ceo/final_report")
        raw = call_llm(
            DEFAULT_PROVIDER, DEFAULT_MODEL, system,
            json.dumps(payload, ensure_ascii=False, indent=2),
            max_tokens=CEO_REPORT_MAX_TOKENS,
        )
        text = _strip_foreign(raw).strip()   # 기존 외래문자 필터 재사용
        if "## 4주 실행 로드맵" in text and "## 핵심 결정 3가지" in text:
            return text
        # 섹션 누락 = 종합 실패로 간주 -> 폴백
    except Exception as e:
        print(f"[CEO._synthesize_final_report] 실패 ({e}) -> 폴백")
    return self._reports.build_final_report(context, get_key_labels())
```

주의:
- _strip_foreign / _FOREIGN_CHAR_RE 는 세션 28에서 ceo.py 에 이미 도입됨 — 재사용.
  (없으면 validators/output_validator 의 외래문자 정규식과 동일 패턴으로 신설)
- call_llm, DEFAULT_PROVIDER, DEFAULT_MODEL, self._prompts, get_key_labels, json 은
  ceo.py 에 이미 import/사용 중 — 추가 import 불필요.
- 폴백은 운영 안전장치다. 절대 제거하지 말 것 (ADR 025 self-review 원칙).

### B1-3. config 상수
src/core/config.py 에 추가:
```python
CEO_REPORT_MAX_TOKENS = 2500   # 종합 리포트는 길다 (CEO_MAX_TOKENS=1000과 별도)
```

### B1-4. report_builder.py
build_final_report 는 변경하지 않는다 (폴백으로 유지). 주석만 1줄 추가:
# 폴백 전용 — 정상 경로는 CEO._synthesize_final_report (LLM 종합)


---

## B2. 실행계획 구조화 (파서 + API)

### B2-1. 신규 파서 모듈
경로: src/core/plan_extractor.py  (결정론적, LLM 미사용 — 매니저 스타일과 일관)

```python
# plan_extractor — 컨셉기획 캘린더 + 최종리포트에서 구조화 실행계획 추출.
# 결정론적(정규식). LLM 미사용. UI 관리 화면용 JSON 생성.
import re

def extract_weeks(concept_output: str) -> list[dict]:
    # 04_컨셉기획.md 의 '#### Week N' 섹션에서 주차별 항목 추출.
    # 반환: [{"num":1,"items":["..."]}, ...] (1~4주, 없으면 빈 items)
    weeks = []
    for n in (1, 2, 3, 4):
        m = re.search(rf"####\s*Week\s*{n}\b", concept_output)
        items = []
        if m:
            rest = concept_output[m.end():]
            nxt = re.search(r"\n####\s|\n###\s", rest)
            body = rest[:nxt.start()] if nxt else rest
            for ln in body.splitlines():
                s = ln.strip()
                if re.match(r"^(\d+\.|[-*])\s+", s):
                    items.append(re.sub(r"^(\d+\.|[-*])\s+", "", s))
        weeks.append({"num": n, "items": items})
    return weeks

def _extract_list_section(report: str, header: str) -> list[str]:
    # 최종리포트에서 '## {header}' 섹션의 리스트 항목 추출.
    m = re.search(rf"##\s*{re.escape(header)}\b", report)
    if not m:
        return []
    rest = report[m.end():]
    nxt = re.search(r"\n##\s", rest)
    body = rest[:nxt.start()] if nxt else rest
    out = []
    for ln in body.splitlines():
        s = ln.strip()
        if re.match(r"^(\d+\.|[-*])\s+", s):
            out.append(re.sub(r"^(\d+\.|[-*])\s+", "", s))
    return out

def extract_plan(concept_output: str = "", final_report: str = "") -> dict:
    return {
        "weeks": extract_weeks(concept_output or ""),
        "next_actions": _extract_list_section(final_report or "", "지금 당장 할 3가지"),
        "kpi": _extract_list_section(final_report or "", "성공 지표 (30일)")
               or _extract_list_section(final_report or "", "성공 지표"),
    }
```

### B2-2. 신규 라우트
경로: src/api/routes/plan.py
```python
from pathlib import Path
import re
from fastapi import APIRouter, HTTPException
from core.config import OUTPUTS_DIR
from core.plan_extractor import extract_plan

router = APIRouter()
_SAFE_NAME = re.compile(r"^[\w가-힯ㄱ-ㅣ_-]+$")

@router.get("/plan/{name}")
async def get_plan(name: str):
    if not _SAFE_NAME.match(name):
        raise HTTPException(status_code=400, detail="Invalid name")
    base = OUTPUTS_DIR / name / "산출물"
    if not base.exists():
        raise HTTPException(status_code=404, detail="No outputs")
    concept = base / "04_컨셉기획.md"
    final = base / "최종리포트.md"
    c = concept.read_text(encoding="utf-8") if concept.exists() else ""
    f = final.read_text(encoding="utf-8") if final.exists() else ""
    return {"influencer": name, **extract_plan(c, f)}
```
주의: 산출물 실제 파일명 확인 — save_final_report / 컨셉기획 저장 파일명이
"최종리포트.md" / "04_컨셉기획.md" 가 맞는지 file_manager 에서 확인 후 상수 일치.

### B2-3. 라우터 등록
src/api/main.py 에서 기존 라우터들과 동일 패턴으로 plan.router include.
(reports/decision/interview 등록부 옆에 추가)


---

## F2. 프론트 컨트롤러 배선 (코덱스 — 뷰 아님)

> MVC 계약: api.js(통신)/actions.js(로직)/model.js(상태)는 코덱스가,
> views.js/style.css(화면)는 Claude Design 이 담당. 본 절은 코덱스 몫.

### model.js — 상태 필드 추가
State 객체에 추가:
```js
plan: null,   // { weeks:[{num,items[]}], next_actions:[], kpi:[] }
```
그리고 Actions.reset() 에 `State.plan = null;` 추가 (actions.js).

### api.js — 메서드 추가
```js
/** GET /api/plan/{name} */
getPlan(name) { return this._req('/plan/' + encodeURIComponent(name)); },
```

### actions.js — 로드 + 자동 호출
```js
async loadPlan(name) {
  const target = name || State.influencerName;
  if (!target) return;
  try { State.plan = await API.getPlan(target); State.notify(); }
  catch (_) { State.plan = null; }
},
```
호출 시점: pushActivity 의 job_completed 분기에서 Actions._loadReports() 다음 줄에
`Actions.loadPlan();` 추가. 부트 복구(main.js)에서 reports 복원 시에도 1회 호출.

---

## 테스트 (코덱스 작성)

### test_plan_extractor.py (단위)
- Week 1~4 정규 파싱: 4개 dict, 항목 추출 정확
- "#### Week 2" 없을 때 해당 주 items=[] (폴백)
- next_actions: "## 지금 당장 할 3가지" 3항목 추출
- kpi: "## 성공 지표 (30일)" 추출, "(30일)" 없는 변형도 폴백 매칭
- 빈 입력 -> weeks 4개(전부 빈 items), next_actions/kpi []
- 테스트 파일 자체 CJK 0

### test_plan_api.py (통합)
- 산출물 픽스처 생성 -> GET /api/plan/{name} 200 + weeks/next_actions/kpi 키 존재
- 산출물 없는 이름 -> 404
- 잘못된 이름(특수문자) -> 400

### 회귀
- 기존 247 테스트 전부 통과
- final_report 포맷 변경이 깨는 기존 테스트 있으면 갱신
  (이어붙이기 가정 -> 6섹션 가정)

---

## 구현 순서 (권장)
1. B2 plan_extractor + test (LLM 불필요 — 빠르고 독립)
2. B2 plan route + main 등록 + test
3. B1 프롬프트 파일 + config 상수
4. B1 ceo._synthesize_final_report + 폴백 + 회귀 테스트
5. F2 컨트롤러 배선 (api/actions/model)
6. E2E 1회: 가상 대상자 -> 종합 리포트 6섹션 + /api/plan JSON 확인
7. status.md 갱신

## 완료 기준 (재확인)
- 종합 리포트 6섹션 생성 + 외래문자 0 + 폴백 동작
- /api/plan 가 weeks/next_actions/kpi 반환
- plan_extractor/plan_api 테스트 PASS + 247 무회귀
- 프론트 State.plan 채워짐 (Claude Design 이 이걸 그림)

## 참조
- Loop: docs/workflow/loops/loop_002_관리중심전환.md
- UI 핸드오프: docs/workflow/step7_구현/핸드오프_v4_관리중심UI.md
- 기존 코드: ceo.py(_finalize), report_builder.py, manager.py(_extract_week_section),
  concept_planner.py(_STEP5_ASSEMBLE 포맷), api/routes/reports.py
