import sys
import io
import re
import time
from pathlib import Path

# Windows: stdout UTF-8 강제 (uvicorn 경유 시 src/main.py의 설정이 적용 안 됨)
# pytest 환경에서는 stdout을 건드리지 않는다 (capture 충돌 방지)
if sys.platform == "win32" and "pytest" not in sys.modules:
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
    except (AttributeError, ValueError):
        pass

# Ensure src/ is on the path when running via uvicorn
_src_dir = str(Path(__file__).resolve().parent.parent)
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from api.routes import ceo, stream, decision, reports, reanalyze, interview, plan, chat, measure, manager
from api.session_manager import SessionManager
from core.config import API_HOST, API_PORT

app = FastAPI(title="Influencer Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{API_PORT}",
        f"http://127.0.0.1:{API_PORT}",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

session_mgr = SessionManager()

ceo.init_router(session_mgr)
stream.init_router(session_mgr)
decision.init_router(session_mgr)
reanalyze.init_router(session_mgr)
interview.init_router(session_mgr)
chat.init_router()

app.include_router(ceo.router, prefix="/api", tags=["ceo"])
app.include_router(stream.router, prefix="/api", tags=["stream"])
app.include_router(decision.router, prefix="/api", tags=["decision"])
app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(plan.router, prefix="/api", tags=["plan"])
app.include_router(reanalyze.router, prefix="/api", tags=["reanalyze"])
app.include_router(interview.router, prefix="/api", tags=["interview"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(measure.router, prefix="/api", tags=["measure"])
app.include_router(manager.router, prefix="/api", tags=["manager"])

static_dir = Path(__file__).parent / "static"

# Cache-busting: serve index.html with a per-boot version token appended to local
# asset URLs so a server restart (i.e. a code change) forces browsers to refetch
# config/api/model/actions/views/main.js + style.css instead of serving stale
# cached copies. CDN (https) assets are left untouched. Registered BEFORE the
# static mount so it wins for exact "/".
_BOOT_TOKEN = str(int(time.time()))
_INDEX_PATH = static_dir / "index.html"


@app.get("/", response_class=HTMLResponse)
async def index():
    html = _INDEX_PATH.read_text(encoding="utf-8")
    html = re.sub(r'(src|href)="(?!https?://)([^"]+)"',
                  rf'\1="\2?v={_BOOT_TOKEN}"', html)
    return HTMLResponse(html)


if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=True)
