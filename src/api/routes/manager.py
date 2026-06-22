import re

from fastapi import APIRouter, HTTPException

from core.config import OUTPUTS_DIR
from core.file_manager import FileManager

router = APIRouter()

_SAFE_NAME = re.compile(r"^[\w가-힯ㄱ-ㅣ_-]+$")


@router.get("/manager/{name}")
async def get_manager_notes(name: str):
    """매니저 알림(.system/manager/*.md) 디스크 복원."""
    if not _SAFE_NAME.match(name):
        raise HTTPException(status_code=400, detail="Invalid name")
    base = OUTPUTS_DIR / name
    if not base.exists():
        return {"influencer": name, "notes": []}
    fm = FileManager(name)
    return {"influencer": name, "notes": fm.load_manager_outputs()}
