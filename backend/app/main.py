import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import auth, classes, faces, lecturers, parents, reports, schedules, sessions, students
from app.api.auth import limiter
from app.core.config import settings
from app.db.database import init_db
from app.services import antispoof_service
from app.services.evidence_cleanup import run_cleanup_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    antispoof_service.warm_up()  # log canh bao ngay neu chua co model, thay vi doi request dau
    cleanup_task = asyncio.create_task(run_cleanup_loop())
    yield
    cleanup_task.cancel()


app = FastAPI(title="FAMS — Face Attendance Management System", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # X-Total-Count: tong so ban ghi cho phan trang (GET /students, /classes,
    # /lecturers, /schedules) - trinh duyet an het header tuy chinh tru khi khai
    # bao o day, du server da tra ve.
    expose_headers=["X-Total-Count"],
)

for router in (auth.router, students.router, classes.router, lecturers.router,
               faces.router, sessions.router, reports.router, schedules.router,
               parents.router):
    app.include_router(router)

os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=settings.EVIDENCE_DIR), name="evidence")


@app.get("/")
def health():
    return {"app": "FAMS", "status": "ok"}
