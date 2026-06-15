"""Measure routes — weekly KPI, per-content log, summary (P1-U4).

Thin HTTP surface over core.measure.MeasureStore. ASCII-only source.
"""
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.measure import MeasureStore, WeeklyKPI, ContentEntry

router = APIRouter()

_SAFE_NAME = re.compile(r"^[\w-]+$")


def _store(name: str) -> MeasureStore:
    if not name or not _SAFE_NAME.match(name):
        raise HTTPException(status_code=400, detail="Invalid influencer name")
    return MeasureStore(name)


class KPIBody(BaseModel):
    week: int
    followers: int = 0
    content_count: int = 0
    total_views: int = 0
    engagement: int = 0
    conversions: int = 0


@router.put("/measure/{name}/kpi")
async def put_kpi(name: str, body: KPIBody):
    store = _store(name)
    store.record_kpi(WeeklyKPI(**body.model_dump()))
    return {"status": "saved", "week": body.week}


class ContentBody(BaseModel):
    date: str
    title: str
    topic: str
    fmt: str
    length: str
    time_slot: str
    views: int = 0
    likes: int = 0
    saves: int = 0
    comments: int = 0
    week: int = 0


@router.post("/measure/{name}/content")
async def post_content(name: str, body: ContentBody):
    store = _store(name)
    store.log_content(ContentEntry(**body.model_dump()))
    return {"status": "saved", "title": body.title}


@router.get("/measure/{name}/summary")
async def get_summary(name: str):
    store = _store(name)
    return {
        "name": name,
        "summary": store.weekly_report(),
        "decision_counts": store.decision_counts(),
        "kpi_weeks": [k.week for k in store.load_kpis()],
        "content_count": len(store.load_contents()),
    }
