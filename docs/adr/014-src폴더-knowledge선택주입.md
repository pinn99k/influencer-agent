# ADR 014 — src/ 폴더 격리 + knowledge 선택 주입 방식
date: 2026-05-14
status: 확정

---

## 컨텍스트

1. 코드·프롬프트·지식베이스가 루트에 docs/ 등과 섞여 있어 빌드 레이어와 런타임 레이어가 혼재
2. CEO가 knowledge/ 전체를 시스템 프롬프트에 주입 시 Groq llama3-70b 컨텍스트 한계(8K~32K) 초과 위험
3. 에이전트가 자율적으로 판단할 수 있도록 prompts + knowledge가 자기완결적 구조여야 함

---

## 결정 1 — src/ 폴더 격리

런타임에 필요한 모든 파일을 `src/` 하나로 격리한다.

```
빌드 레이어 (인간·Claude Code용)
  CLAUDE.md / .claude/ / docs/

런타임 레이어 (에이전트 실행용)
  src/
    main.py / core/ / agents/ / validators/
    prompts/    ← 역할·형식·사고구조
    knowledge/  ← 판단 근거 전문지식
    outputs/    ← 런타임 산출물
```

**실행 명령:** `cd src && python main.py`

**근거:**
- 빌드 문서(workflow, adr, review)가 에이전트 런타임과 무관
- src/ 안에서만 실행하면 Path("outputs/...") 등 상대경로 일관성 보장
- 도메인 교체 시 src/ 전체 교체로 대응 가능

---

## 결정 2 — knowledge 선택 주입 방식

전체 로드 금지. 판단 유형에 따라 관련 지식만 선택 주입.

### 하위 에이전트

init 시 자기 역할 지식만 로드 (소량, 고정).

```python
# base_agent.py
class BaseAgent(ABC):
    knowledge_dir: str = ""  # "부서/기획본부/대상분석"

    def __init__(self):
        self.system_prompt = self._load_template() + self._load_knowledge()

    def _load_knowledge(self) -> str:
        """src/knowledge/{knowledge_dir}/ 하위 .md 전부 읽어 병합"""
        if not self.knowledge_dir:
            return ""
        base = Path("knowledge") / self.knowledge_dir
        if not base.exists():
            return ""
        parts = [p.read_text(encoding="utf-8") for p in sorted(base.glob("*.md"))]
        return "\n\n---\n\n".join(parts)
```

### CEO

판단 유형별로 관련 경영 지식 섹션만 동적 로드.

```python
# ceo.py
KNOWLEDGE_MAP = {
    "전략수립": ["경영/01_전략경영", "경영/06_운영관리"],
    "품질판단": ["경영/05_품질관리", "경영/08_의사결정"],
    "보고판단": ["경영/07_리스크관리", "경영/09_커뮤니케이션"],
    "ROI판단":  ["경영/03_재무관리", "경영/04_조직인사관리"],
}

def _load_knowledge_for(self, judgment_type: str) -> str:
    """판단 유형에 맞는 지식만 로드하여 반환"""
    dirs = KNOWLEDGE_MAP.get(judgment_type, [])
    parts = []
    for d in dirs:
        path = Path("knowledge") / d
        if path.exists():
            parts += [p.read_text(encoding="utf-8") for p in sorted(path.glob("*.md"))]
    return "\n\n---\n\n".join(parts)
```

**근거:**
- 경영 9카테고리 전체 로드 시 토큰 초과 가능 → 판단 시점마다 필요한 것만
- 하위 에이전트는 자기 도메인만 알면 됨 (소량) → init 시 1회 로드 허용
- 판단 유형이 명확하므로 선택 기준 구체적 정의 가능

---

## 결정 3 — prompts/ 구조

```
src/prompts/
├── ceo/
│   ├── goal_interpretation.md
│   └── next_decision.md
└── 부서/
    └── 기획본부/
        ├── 대상분석.md
        ├── 경쟁분석.md
        ├── 플랫폼추천.md
        └── 컨셉기획.md
```

부서 추가 = 폴더 하나 추가. 기존 코드 수정 없음.

---

## 영향 범위

| 파일 | 변경 |
|------|------|
| `step6_아키텍처/아키텍처.md` | 파일트리 + base_agent + CEO knowledge 로직 반영 |
| `step5_기술결정/흐름정리.md` | 파일트리 + 참조 경로 수정 |
| `CLAUDE.md` | Structure + 실행 명령 + task_units 경로 |
| `step4/CEO/00_요약.md` | 도메인 지식 경로 참조 수정 |
