import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

from core.config import OUTPUTS_DIR

router = APIRouter()

_SAFE_NAME = re.compile(r"^[\w가-힯ㄱ-ㅣ_-]+$")
_SAFE_FILE = re.compile(r"^[\w가-힯ㄱ-ㅣ_.()-]+\.md$")


def _validate_name(name: str) -> str:
    if not _SAFE_NAME.match(name):
        raise HTTPException(status_code=400, detail="Invalid influencer name")
    return name


def _validate_filename(filename: str) -> str:
    if not _SAFE_FILE.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return filename


@router.get("/reports/{influencer_name}")
async def list_reports(influencer_name: str):
    name = _validate_name(influencer_name)
    deliverables_dir = OUTPUTS_DIR / name / "산출물"
    if not deliverables_dir.exists():
        raise HTTPException(status_code=404, detail="No reports found")

    files = sorted(
        f.name for f in deliverables_dir.iterdir()
        if f.is_file() and f.suffix == ".md"
    )
    return {"influencer": name, "reports": files}


@router.get("/reports/{influencer_name}/{filename}")
async def get_report(influencer_name: str, filename: str):
    name = _validate_name(influencer_name)
    fname = _validate_filename(filename)
    path = OUTPUTS_DIR / name / "산출물" / fname

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")

    content = path.read_text(encoding="utf-8")
    return {"filename": fname, "content": content}
