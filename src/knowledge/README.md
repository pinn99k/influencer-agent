# Knowledge Base — 지식 도메인 구조
# 목적: 에이전트 판단 근거 지식의 표준 구조. 에이전트 분할 시에도 일관 유지.
updated: 2026-05-29

---

## 트리 구조

```
knowledge/
├── management/            ← CEO(경영) 도메인. 9개 카테고리 × (개념.md + 프레임워크.md)
│                             CEO가 KNOWLEDGE_MAP 기준 선택 주입 (core/prompt_loader.py)
└── dept/                  ← 부서별 직무 에이전트 도메인
    └── {부서}/            ← 예: planning(기획본부). 향후 marketing·finance 등 추가
        └── {에이전트}/    ← 예: subject_analysis. BaseAgent.knowledge_dir가 가리킴
            ├── 프레임워크/  ← 범용 사고틀·방법론 (직업 무관). 분할 시 재사용 핵심
            ├── 사례/        ← 구체 업종 사례·참고 (미용사 등)
            └── 출력/        ← 출력형식.md + 예시.md (산출물 스캐폴딩)
```

---

## 로딩 방식

- 직무 에이전트: `BaseAgent._load_knowledge`가 `knowledge_dir` 하위를 **rglob 재귀** 로딩.
  → 프레임워크/사례/출력 3개 하위 폴더의 모든 .md가 시스템 프롬프트에 병합됨.
- CEO: `PromptLoader.load_knowledge_for`가 `management/{카테고리}`를 평면 glob 로딩.

---

## 카테고리 원칙

| 폴더 | 성격 | 에이전트 분할 시 |
|------|------|----------------|
| 프레임워크/ | 범용 원리·사고틀 (어느 직업에도 적용) | 새 에이전트가 그대로 상속·공유 |
| 사례/ | 특정 업종의 구체 예시 | 업종별로 추가 |
| 출력/ | 산출물 형식·예시 (에이전트 전용) | 에이전트와 함께 이동 |

핵심: **범용(프레임워크)와 구체(사례)를 분리**한다. 범용 프레임워크가 두터울수록
프롬프트는 얇은 역할가이드로 갈 수 있고(output_quality = context_quality × prompt_quality),
에이전트를 분할해도 도메인 지식이 깨지지 않는다.

---

## 네이밍 규칙

- 폴더·파일명 한글 허용. 한자(CJK U+4E00~U+9FFF) 절대 금지.
- 모든 파일은 Python `write_text(encoding="utf-8")`로만 작성 (Edit/PowerShell 금지).

---

## 에이전트 분할 시 절차

1. `dept/{부서}/{새에이전트}/` 폴더 생성
2. `프레임워크/` `사례/` `출력/` 3개 하위 폴더 구성
3. 공유 가능한 범용 프레임워크는 복사 또는 상위 공통 폴더 참조 (방식 추후 결정)
4. `BaseAgent.knowledge_dir = "dept/{부서}/{새에이전트}"` 설정
5. `agents/agent_context.py`의 AGENT_SCOPES에 knowledge 경로 등록
