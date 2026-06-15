# ADR 017 — Agent Registry 패턴
date: 2026-05-16 (세션 16)
status: 확정

---

## 결정

`agents/__init__.py`에 `AGENT_CLASSES` 리스트를 두고,
에이전트 메타데이터(display_name, context_key, output_prefix, output_label)를
이 리스트 하나에서 파생한다.

---

## 문제

세션 14까지 에이전트 1개 추가 시 수동으로 7곳을 동기화해야 했다:

| 위치 | 수정 내용 |
|------|-----------|
| `agents/ceo.py` | import + agents dict 추가 |
| `agents/ceo.py` | AGENT_KEY_MAP 항목 추가 |
| `agents/ceo.py` | AGENT_ORDER 항목 추가 |
| `agents/ceo.py` | build_final_report key_labels 추가 |
| `core/file_manager.py` | num_map 항목 추가 |
| `main.py` | init_context() 키 추가 |
| `tests/conftest.py` | SAMPLE_CONTEXT 키 추가 |

한 곳이라도 빠지면 런타임 에러 또는 silent bug.

---

## 결정 근거

- 에이전트 메타데이터는 에이전트 클래스 자체에 있는 것이 자연스러움
- `AGENT_CLASSES` 리스트가 순서·메타데이터 SSoT
- `get_agent_order()`, `get_context_keys()`, `get_key_labels()`로 파생
- 에이전트 추가 시 수정 위치: Registry 1곳 + `OutputValidator.RULES` 1곳 = **2곳**

---

## 구현

```python
# agents/__init__.py
AGENT_CLASSES = [
    SubjectAnalystAgent,
    CompetitionAnalystAgent,
    PlatformRecommenderAgent,
    ConceptPlannerAgent,
]

def get_agent_order() -> list[str]:
    return [cls.display_name for cls in AGENT_CLASSES]

def get_context_keys() -> list[str]:
    return [cls.context_key for cls in AGENT_CLASSES]

def get_key_labels() -> list[tuple[str, str]]:
    return [(cls.context_key, cls.output_label) for cls in AGENT_CLASSES]
```

```python
# agents/base_agent.py — 새 클래스 변수
class BaseAgent(ABC):
    context_key:   str = ""    # context dict 저장 키
    output_prefix: str = "00"  # 산출물 파일 번호
    output_label:  str = ""    # 최종 리포트 표시명
```

---

## 트레이드오프

| 장점 | 단점 |
|------|------|
| 에이전트 추가 비용 7→2곳 | __init__.py import 순서 주의 (순환 import 가능성) |
| 메타데이터 단일 소유자 명확 | 클래스 변수 미설정 시 BaseAgent 기본값으로 silently fallthrough |
| 테스트에서 레지스트리 재사용 가능 | |

---

## 영향 범위

- `agents/ceo.py`: AGENT_KEY_MAP 제거, AGENT_ORDER = get_agent_order()
- `core/file_manager.py`: save_output(prefix, agent_name, content)
- `core/report_builder.py`: build_final_report(context, key_labels)
- `main.py`: init_context()에서 get_context_keys() 사용
- `tests/conftest.py`: SAMPLE_CONTEXT 빌드에 get_context_keys() 사용
