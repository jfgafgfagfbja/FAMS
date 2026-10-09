import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError

from app.api import (auth, classes, faces, lecturers, locations, media, notifications,
                     parents, reports, rooms, schedules, sessions, staff, students, units)
from app.api.auth import limiter
from app.core.config import settings
from app.db.database import init_db
from app.services import antispoof_service, email_service
from app.services.evidence_cleanup import run_cleanup_loop
# Import la du: module tu gan bo bat su kien sinh thong bao cho phu huynh vao SQLAlchemy.
from app.services.parent_notify import run_notification_email_loop
from app.services.session_service import run_auto_close_loop

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    antispoof_service.warm_up()  # log canh bao ngay neu chua co model, thay vi doi request dau
    tasks = []
    if settings.BACKGROUND_JOBS_ENABLED:
        tasks = [asyncio.create_task(run_cleanup_loop()),
                 asyncio.create_task(run_auto_close_loop())]
        if email_service.is_configured():
            tasks.append(asyncio.create_task(run_notification_email_loop()))
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(title="FAMS — Face Attendance Management System", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Luoi an toan: vi pham rang buoc DB chua duoc kiem tra truoc o endpoint (trung
    khoa, khoa ngoai dang duoc tham chieu...) tra 409 thay vi 500."""
    logger.warning("IntegrityError tai %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(
        status_code=409,
        content={"detail": "Du lieu bi trung hoac dang duoc su dung o noi khac"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # X-Total-Count: tong so ban ghi cho phan trang (GET /students, /classes,
    # /lecturers, /schedules...) - trinh duyet an het header tuy chinh tru khi khai
    # bao o day, du server da tra ve. Content-Disposition: ten file Excel khi tai ve.
    expose_headers=["X-Total-Count", "Content-Disposition"],
)

for router in (auth.router, students.router, classes.router, lecturers.router,
               faces.router, sessions.router, reports.router, schedules.router,
               parents.router, units.router, staff.router, locations.router, rooms.router,
               notifications.router, media.router):
    app.include_router(router)


@app.get("/")
def health():
    return {"app": "FAMS", "status": "ok"}
