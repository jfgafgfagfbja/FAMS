"""Don anh bang chung qua han luu tru (xem docs/FAMS-thiet-ke.md: "anh bang chung luu co thoi han")."""
import asyncio
import os
import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.db.database import SessionLocal

CLEANUP_INTERVAL_SECONDS = 24 * 3600


def cleanup_expired_evidence(db: Session) -> int:
    """Xoa file anh bang chung qua han va don duong dan tuong ung trong DB. Tra ve so file da xoa."""
    if not os.path.isdir(settings.EVIDENCE_DIR):
        return 0

    cutoff = time.time() - settings.EVIDENCE_RETENTION_DAYS * 86400
    deleted = 0

    for root, _dirs, files in os.walk(settings.EVIDENCE_DIR):
        for filename in files:
            path = os.path.join(root, filename)
            if os.path.getmtime(path) >= cutoff:
                continue
            rel_within_evidence = os.path.relpath(path, settings.EVIDENCE_DIR).replace("\\", "/")
            rel_url = f"/evidence/{rel_within_evidence}"
            os.remove(path)
            deleted += 1
            (
                db.query(models.AttendanceRecord)
                .filter(models.AttendanceRecord.evidence_image == rel_url)
                .update({"evidence_image": ""})
            )

    if deleted:
        db.commit()
    return deleted


async def run_cleanup_loop() -> None:
    """Vong lap nen: don anh het han moi 24h (chay ngay 1 lan luc khoi dong)."""
    while True:
        db = SessionLocal()
        try:
            cleanup_expired_evidence(db)
        except Exception:
            pass
        finally:
            db.close()
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
