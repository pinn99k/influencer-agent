import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config import OUTPUTS_DIR
from core.file_manager import FileManager
from core.direction import direction_has_content

router = APIRouter()

_session_mgr = None

_SAFE_NAME = re.compile(r"^[\w가-힯ㄱ-ㅣ_-]+$")


def init_router(session_manager):
    global _session_mgr
    _session_mgr = session_manager


def _validate_name(name: str) -> str:
    if not _SAFE_NAME.match(name):
        raise HTTPException(status_code=400, detail="Invalid influencer name")
    return name


def _has_reanalyze_input(name: str, body_feedback: str | None) -> bool:
    """재분석을 정당화하는 새 입력이 하나라도 있는가 (성과/피드백/방향)."""
    if (body_feedback or "").strip():
        return True
    fm = FileManager(name)
    if (fm.load_feedback() or "").strip():
        return True
    perf = OUTPUTS_DIR / name / "성과기록.md"
    if perf.exists() and perf.read_text(encoding="utf-8").strip():
        return True
    if direction_has_content(fm.load_direction() or ""):
        return True
    return False


# ── GET /api/subjects ────────────────────────────────────────────


@router.get("/subjects")
async def list_subjects():
    """outputs/ 폴더를 스캔해서 기존 대상자 목록 반환."""
    if not OUTPUTS_DIR.exists():
        return {"subjects": []}

    subjects = []
    for child in sorted(OUTPUTS_DIR.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue

        has_outputs = (child / "산출물").exists() and any(
            f.suffix == ".md" for f in (child / "산출물").iterdir()
        ) if (child / "산출물").exists() else False

        has_feedback = (child / "피드백.md").exists()
        has_performance = (child / "성과기록.md").exists()
        dir_path = child / "방향.md"
        has_direction = (
            direction_has_content(dir_path.read_text(encoding="utf-8"))
            if dir_path.exists() else False
        )

        subjects.append({
            "name": child.name,
            "has_outputs": has_outputs,
            "has_feedback": has_feedback,
            "has_performance": has_performance,
            "has_direction": has_direction,
        })

    return {"subjects": subjects}


# ── POST /api/reanalyze ─────────────────────────────────────────


class ReanalyzeRequest(BaseModel):
    name: str
    feedback: str | None = None


@router.post("/reanalyze")
async def start_reanalyze(request: ReanalyzeRequest):
    """재분석 잡 시작. feedback이 있으면 피드백.md에 저장 후 재분석."""
    name = _validate_name(request.name)

    # 기존 산출물이 있는지 확인
    deliverables_dir = OUTPUTS_DIR / name / "산출물"
    if not deliverables_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No existing outputs for '{name}'. Run initial analysis first.",
        )

    # 재분석 전제조건: 새 입력(성과/피드백/방향) 중 하나는 있어야 한다.
    # 아무 입력도 없으면 같은 결과를 다시 뽑을 뿐 -> 잡 시작 전에 막는다.
    if not _has_reanalyze_input(name, request.feedback):
        raise HTTPException(
            status_code=400,
            detail="재분석하려면 성과·피드백·방향 중 하나는 입력해야 합니다.",
        )

    try:
        job_id = _session_mgr.start_reanalyze_job(name, feedback=request.feedback)
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    return {"job_id": job_id, "status": "started"}


# ── GET/PUT /api/feedback/{name} ────────────────────────────────


@router.get("/feedback/{name}")
async def get_feedback(name: str):
    """피드백.md 내용 로드."""
    name = _validate_name(name)
    fm = FileManager(name)
    content = fm.load_feedback()
    return {"name": name, "content": content}


class FeedbackBody(BaseModel):
    content: str


@router.put("/feedback/{name}")
async def save_feedback(name: str, body: FeedbackBody):
    """피드백.md 내용 저장."""
    name = _validate_name(name)
    fm = FileManager(name)
    path = fm.save_feedback(body.content)
    return {"status": "saved", "path": str(path)}


# ── GET/PUT /api/direction/{name} ───────────────────────────────


@router.get("/direction/{name}")
async def get_direction(name: str):
    """방향.md 내용 로드. 사용자가 정한 전략 방향."""
    name = _validate_name(name)
    fm = FileManager(name)
    return {"name": name, "content": fm.load_direction()}


class DirectionBody(BaseModel):
    content: str


@router.put("/direction/{name}")
async def save_direction(name: str, body: DirectionBody):
    """방향.md 내용 저장. 다음 재분석에서 전략에 반영됨."""
    name = _validate_name(name)
    fm = FileManager(name)
    path = fm.save_direction(body.content)
    # Provenance: a direction change is a HUMAN strategy decision (measure layer).
    try:
        from core.measure import MeasureStore, DecisionEntry, ACTOR_HUMAN
        first_line = next(
            (ln.strip() for ln in body.content.splitlines()
             if ln.strip() and not ln.strip().startswith("#")),
            body.content.strip()[:80],
        )
        MeasureStore(name).log_decision(DecisionEntry(
            actor=ACTOR_HUMAN, basis="사용자 직접 설정",
            decision=f"방향 변경: {first_line[:120]}",
        ))
    except Exception:
        pass
    return {"status": "saved", "path": str(path)}


# ── GET/PUT /api/performance/{name} ─────────────────────────────


@router.get("/performance/{name}")
async def get_performance(name: str):
    """성과기록.md 내용 로드."""
    name = _validate_name(name)
    path = OUTPUTS_DIR / name / "성과기록.md"
    content = path.read_text(encoding="utf-8") if path.exists() else None
    return {"name": name, "content": content}


class PerformanceBody(BaseModel):
    content: str


@router.put("/performance/{name}")
async def save_performance(name: str, body: PerformanceBody):
    """성과기록.md 내용 저장."""
    name = _validate_name(name)
    path = OUTPUTS_DIR / name / "성과기록.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.content, encoding="utf-8")
    return {"status": "saved", "path": str(path)}
