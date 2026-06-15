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
    concept_text = concept.read_text(encoding="utf-8") if concept.exists() else ""
    final_text = final.read_text(encoding="utf-8") if final.exists() else ""
    return {"influencer": name, **extract_plan(concept_text, final_text)}
