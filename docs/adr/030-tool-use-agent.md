# ADR 030 — Tool-Use Agent 전환 (에이전트 파일 접근 능력 부여)
# (원래 022로 작성됨 — 번호 충돌로 030 재번호. 세션 26 제안, 2장(ADR 029) 하네스로 흡수)
# 상태: 제안 (세션 26)
# 결정일: 2026-05-26
# 맥락: Spiral 4-B 이후, 유료 API 전환 + 품질 개선 방향

---

## 요약

에이전트에 파일 시스템 도구(읽기/쓰기/탐색)를 부여하여,
현재 "knowledge 하드 주입 -> LLM 1회 호출" 구조를
"에이전트가 필요한 정보를 스스로 탐색하고 참조하며 작업" 구조로 전환한다.

---

## 현재 구조 (As-Is)

```
main.py -> CEO.run(context)
  -> PlanningDepartment.run(context)
       -> per agent:
            1. BaseAgent.__init__(): knowledge 전체 로드 (고정)
            2. build_prompt(context): user_prompt 조합
            3. call_llm(system_prompt + knowledge, user_prompt)
            4. 결과 -> validator -> 저장
```

### 한계
- knowledge 전체를 system_prompt에 주입 -> 토큰 비용 높음 (66KB)
- 에이전트가 어떤 정보가 필요한지 스스로 판단 불가
- CEO는 계획만 세우고, 파일을 직접 읽거나 편집 불가
- 새 정보원 추가 시 코드 수정 필요 (knowledge_dir 하드코딩)

---

## 목표 구조 (To-Be)

```
main.py -> CEO.run(context)
  -> CEO:
       1. 프로젝트 폴더 탐색 (list_files, read_file)
       2. 계획 수립 (plan.md 작성/편집)
       3. 하위 에이전트에 역할 + 참고 파일 경로 위임
  -> PlanningDepartment.run(context, plan)
       -> per agent:
            1. CEO 지정 파일 + 자율 탐색으로 컨텍스트 수집
            2. LLM 호출 (필요한 정보만 포함 -> 토큰 절감)
            3. 결과 -> validator -> 파일 저장
```

---

## 핵심 설계 결정

### 1. Tool 정의 (에이전트가 사용 가능한 도구)

| Tool | 설명 | CEO | 하위 에이전트 |
|------|------|-----|------------|
| list_files(path) | 디렉토리 내 파일 목록 반환 | O | O |
| read_file(path) | 파일 내용 읽기 | O | O |
| write_file(path, content) | 파일 생성/덮어쓰기 | O | X (CEO만) |
| edit_file(path, old, new) | 파일 부분 수정 | O | X (CEO만) |
| search_web(query) | 웹 검색 (Serper) | X | O (경쟁분석만) |

**원칙:** 하위 에이전트는 읽기 전용. 쓰기는 CEO만.
**이유:** 하위 에이전트가 서로의 산출물을 덮어쓰면 상태 추적 불가.

### 2. Tool Calling 방식

**선택: LLM Function Calling 패턴 (ReAct)**

```
Thought -> Action -> Observation -> ... -> Final Answer
```

에이전트가 LLM에게 사용 가능한 도구 목록을 system_prompt에 명시.
LLM이 JSON으로 도구 호출을 요청 -> 코드가 실행 -> 결과를 다시 LLM에 전달.

**기각된 대안:** 코드에서 if-else로 단계별 하드코딩
-> 기각 이유: 에이전트 자율성 없음. 새 파일 구조에 대응 불가.

### 3. CEO 계획 수립 흐름

```
Phase 1: 탐색
  CEO가 outputs/{name}/ 폴더 탐색
  기존 산출물 존재 여부 확인 (재분석 모드 판단)
  knowledge/ 폴더 구조 파악

Phase 2: 계획 작성
  plan.md에 구조화된 계획 저장:
  - 각 에이전트별 목표
  - 참고할 파일 경로 목록
  - 의존 관계 (순서)
  - 성공 기준

Phase 3: 위임
  PlanningDepartment에 plan 전달
  각 에이전트는 plan에서 자기 섹션 읽고 실행
```

### 4. 하위 에이전트 파일 접근 전략

**혼합 방식: CEO 범위 지정 + 에이전트 자율 탐색**

```python
# CEO가 plan에서 지정하는 것:
agent_plan = {
    "대상분석": {
        "목표": "대상자 강점/약점/차별점 분석",
        "참고_파일": [
            "knowledge/부서/기획본부/대상분석/분석방법론.md",
            "outputs/{name}/성과기록.md"  # 재분석 시
        ],
        "탐색_허용_범위": ["knowledge/부서/기획본부/대상분석/"]
    }
}

# 에이전트가 자율적으로 하는 것:
# 1. CEO 지정 파일 읽기
# 2. 탐색_허용_범위 내에서 추가 파일 탐색 (list_files -> read_file)
# 3. 필요하다고 판단한 파일만 선택적으로 읽기
```

**이유:**
- CEO가 범위를 제한하므로 에이전트가 무관한 파일을 읽는 낭비 방지
- 범위 내에서는 자율 탐색 허용 -> 새 파일 추가 시 코드 수정 불필요

### 5. ReAct Loop 구현

```python
class ToolUseAgent(BaseAgent):
    """Tool-use capable agent. ReAct loop with max_iterations."""

    max_iterations: int = 5  # 무한 루프 방지
    available_tools: list[str] = ["list_files", "read_file"]

    def run(self, context: dict) -> str:
        messages = [self._build_initial_prompt(context)]

        for i in range(self.max_iterations):
            response = call_llm_with_tools(messages, self.available_tools)

            if response.type == "final_answer":
                return response.content

            if response.type == "tool_call":
                observation = self._execute_tool(response.tool, response.input)
                messages.append({"role": "tool", "content": observation})

        # max_iterations 도달 -> 마지막 응답 반환
        return self._force_final_answer(messages)
```

---

## 구현 계획

### 세션 27: 계획 수립 + 1차 구현

| # | 작업 | 파일 | 난이도 |
|---|------|------|--------|
| 1 | Tool 인터페이스 정의 | src/core/tools.py (신규) | 낮음 |
| 2 | CEO tool-use 능력 추가 | src/agents/ceo.py | 중간 |
| 3 | CEO 계획 수립 Phase 1~3 구현 | src/agents/ceo.py | 중간 |
| 4 | BaseAgent에 tool-use 옵션 추가 | src/agents/base_agent.py | 중간 |
| 5 | 하위 에이전트 1개 (대상분석) tool-use 전환 | src/agents/subject_analyst.py | 중간 |

### 세션 28: 테스트 + 품질 + 나머지 에이전트

| # | 작업 | 파일 |
|---|------|------|
| 6 | 나머지 3개 에이전트 tool-use 전환 | competition/platform/concept |
| 7 | E2E 테스트 + 품질 평가 | tests/ |
| 8 | 품질 미달 시 프롬프트 조정 | prompts/ |

### 세션 29: 마무리 + P0 잔여

| # | 작업 |
|---|------|
| 9 | P0-3: 성과 기록 구조 (tool로 읽기/쓰기) |
| 10 | P0-4: 재분석 모드 (CEO가 기존 산출물 읽고 판단) |
| 11 | 문서 업데이트 (아키텍처.md, status.md) |

---

## 아키텍처 변경 요약

### 신규 파일

```
src/core/tools.py              <- Tool 인터페이스 + 구현체
```

### 변경 파일

```
src/agents/base_agent.py       <- ToolUseAgent 믹스인 or 서브클래스 추가
src/agents/ceo.py              <- tool-use 기반 계획 수립 + 파일 편집
src/departments/planning.py    <- plan 기반 에이전트 실행
src/core/llm_client.py         <- tool calling 지원 (messages 배열 + tool_results)
src/core/config.py             <- TOOL_MAX_ITERATIONS, ALLOWED_PATHS 추가
```

### 의존 방향 (변경 없음)

```
main.py -> CEO -> [departments, agents, validators, core]
agents/ -> core/
core/tools.py -> (의존 없음 -- 순수 파일 연산)
```

---

## Tool 보안 제약

| 제약 | 이유 |
|------|------|
| 경로 허용 목록 (ALLOWED_PATHS) | src/ 바깥 접근 방지 |
| 하위 에이전트 쓰기 금지 | 상태 꼬임 방지 |
| max_iterations 필수 | 무한 루프 방지 |
| ../ 경로 차단 (path traversal) | 보안 |
| 파일 크기 제한 (읽기 시 max 10KB) | 토큰 폭발 방지 |

---

## 트레이드오프

| 얻는 것 | 잃는 것 |
|---------|---------|
| 에이전트 자율성 | 실행 시간 (multi-turn) |
| 토큰 효율 (필요한 것만 읽기) | LLM 호출 수 (tool loop) |
| 새 파일 추가 시 코드 수정 불필요 | 디버깅 복잡도 |
| CEO가 산출물 직접 검토/수정 가능 | tool call 파싱 에러 가능성 |
| 재분석 모드 자연스럽게 지원 | 비용 (유료 API 필수) |

---

## 비용 예측

| 시나리오 | 호출 수 | 예상 비용 (Gemini 2.5 Flash) |
|---------|--------|---------------------------|
| 현재 (single-call) | ~14회 | ~$0.01 |
| tool-use (agent당 3-5 turn) | ~30-50회 | ~$0.03-0.05 |
| 최악 (max_iterations 도달) | ~70회 | ~$0.07 |

여전히 사실상 무료 수준. 유료 API 비용 이슈 없음.

---

## 성공 기준

1. CEO가 outputs/ 폴더를 읽고 재분석 여부를 자율 판단
2. 하위 에이전트가 knowledge/ 내 관련 파일을 스스로 선택해서 참조
3. E2E 품질 점수 80+ 유지 (현재 대비 저하 없음)
4. 기존 단위 테스트 117/118 유지 (회귀 없음)
5. 새 knowledge 파일 추가 시 코드 수정 0줄

---

## 참조

- 현재 아키텍처: docs/workflow/step6_아키텍처/아키텍처.md
- 에이전트 설계 원칙: docs/refs/에이전트_설계원칙.md
- 실전 적용 로드맵: docs/refs/실전적용_로드맵.md
- ADR 014: src폴더 knowledge 선택주입 (이전 결정 -- 이번에 진화)
- ADR 021: multi-step agent knowledge (이전 결정 -- tool-use로 대체)
