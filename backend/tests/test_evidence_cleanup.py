import os
import time
from datetime import datetime

from app.core.config import settings
from app.db import models
from app.services.evidence_cleanup import cleanup_expired_evidence


def test_cleanup_deletes_old_files_and_clears_db_reference(db_session, seed, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EVIDENCE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "EVIDENCE_RETENTION_DAYS", 30)

    session_dir = tmp_path / "1"
    session_dir.mkdir()
    old_file = session_dir / "old.jpg"
    new_file = session_dir / "new.jpg"
    old_file.write_bytes(b"x")
    new_file.write_bytes(b"x")

    old_time = time.time() - 40 * 86400
    os.utime(old_file, (old_time, old_time))

    session = models.AttendanceSession(schedule_id=seed["schedule1_id"], session_date=datetime.now().date())
    db_session.add(session)
    db_session.flush()
    record = models.AttendanceRecord(
        session_id=session.id, student_id=seed["sv1_id"], status="present",
        evidence_image="/evidence/1/old.jpg",
    )
    db_session.add(record)
    db_session.commit()

    deleted = cleanup_expired_evidence(db_session)

    assert deleted == 1
    assert not old_file.exists()
    assert new_file.exists()
    db_session.refresh(record)
    assert record.evidence_image == ""


def test_cleanup_keeps_recent_files(db_session, seed, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "EVIDENCE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "EVIDENCE_RETENTION_DAYS", 90)

    session_dir = tmp_path / "1"
    session_dir.mkdir()
    (session_dir / "recent.jpg").write_bytes(b"x")

    assert cleanup_expired_evidence(db_session) == 0
    assert (session_dir / "recent.jpg").exists()
