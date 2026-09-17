import re
from datetime import datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from passlib.context import CryptContext

from app.api.auth import limiter, reset_login_failures
from app.core import security
from app.core.security import hash_password
from app.db import models
from app.db.database import Base, get_db
from app.core.config import settings
from app.main import app

# Test khong chay vong lap nen (don anh, tu dong dong phien) - chung dung SessionLocal
# tro vao DB dev that, khong phai DB test.
settings.BACKGROUND_JOBS_ENABLED = False
# bcrypt mac dinh 12 vong (~0.25s/lan) - moi test tao 5 tai khoan + dang nhap nen cham;
# 4 vong la muc toi thieu cua bcrypt, chi ap dung trong test.
security.pwd_context = CryptContext(schemes=["bcrypt"], bcrypt__rounds=4)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Login limiter dung storage chung theo process; reset truoc moi test de tranh anh huong cheo."""
    limiter.reset()
    reset_login_failures()
    yield

TEST_DB_NAME = "fams_test"
TEST_DB_URL = re.sub(r"/[^/]+$", f"/{TEST_DB_NAME}", settings.DATABASE_URL)
ADMIN_DB_URL = re.sub(r"/[^/]+$", "/postgres", settings.DATABASE_URL)


@pytest.fixture(scope="session")
def test_engine():
    admin_engine = create_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    admin_engine.dispose()

    engine = create_engine(TEST_DB_URL)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(engine)

    yield engine

    engine.dispose()
    admin_engine = create_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    admin_engine.dispose()


@pytest.fixture()
def db_session(test_engine):
    """Moi test chay trong 1 transaction ngoai, roi lai sau khi xong (kem ca db.commit() ben trong app)."""
    connection = test_engine.connect()
    outer_tx = connection.begin()
    Session = sessionmaker(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")
    session = Session()

    yield session

    session.close()
    outer_tx.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seed(db_session):
    """Du lieu toi thieu: 1 admin, 2 giang vien (2 lop khac nhau), 2 sinh vien, lich hoc."""
    db = db_session

    admin = models.User(email="admin@test.local", password_hash=hash_password("admin123"),
                        role="admin", full_name="Admin Test")
    gv1_user = models.User(email="gv1@test.local", password_hash=hash_password("gv123"),
                           role="lecturer", full_name="GV Mot")
    gv2_user = models.User(email="gv2@test.local", password_hash=hash_password("gv123"),
                           role="lecturer", full_name="GV Hai")
    sv1_user = models.User(email="sv1@test.local", password_hash=hash_password("sv123"),
                           role="student", full_name="SV Mot")
    sv2_user = models.User(email="sv2@test.local", password_hash=hash_password("sv123"),
                           role="student", full_name="SV Hai")
    db.add_all([admin, gv1_user, gv2_user, sv1_user, sv2_user])
    db.flush()

    gv1 = models.Lecturer(user_id=gv1_user.id, lecturer_code="GV01", department="CNTT")
    gv2 = models.Lecturer(user_id=gv2_user.id, lecturer_code="GV02", department="CNTT")
    db.add_all([gv1, gv2])
    db.flush()

    sv1 = models.Student(user_id=sv1_user.id, student_code="SV0001", major="CNTT", cohort=2024)
    sv2 = models.Student(user_id=sv2_user.id, student_code="SV0002", major="CNTT", cohort=2024)
    db.add_all([sv1, sv2])
    db.flush()

    class1 = models.Class(class_code="C1", subject_name="Mon 1", lecturer_id=gv1.id, semester="2026.1")
    class2 = models.Class(class_code="C2", subject_name="Mon 2", lecturer_id=gv2.id, semester="2026.1")
    db.add_all([class1, class2])
    db.flush()

    db.add(models.Enrollment(student_id=sv1.id, class_id=class1.id))

    # open_session gio chi cho mo phien: dung ngay hom nay, dung thu, trong khung
    # [start - EARLY_OPEN_MINUTES, end]. Neo lich vao "bay gio" de cac test mo phien
    # qua API van hop le: bat dau ~10 phut nua (nam trong khung mo som, va check-in
    # ngay sau do van truoc gio hoc -> "present"), ket thuc ~3 tieng nua. Clamp ve
    # cuoi ngay de gio khong trao nguoc khi test chay sat nua dem.
    now = datetime.now()
    start_dt = now + timedelta(minutes=10)
    end_dt = now + timedelta(hours=3)
    sched_start = (start_dt.time().replace(microsecond=0)
                   if start_dt.date() == now.date() else time(23, 58))
    sched_end = (end_dt.time().replace(microsecond=0)
                 if end_dt.date() == now.date() else time(23, 59, 59))

    schedule1 = models.Schedule(class_id=class1.id, weekday=now.weekday(),
                                start_time=sched_start, end_time=sched_end, room="P101")
    # schedule2 co y de vao thu KHAC hom nay - khong test nao can mo phien cho no
    # qua API (chi dung kiem tra 403/CRUD), va giu duoc tinh "2 lich khac thu".
    schedule2 = models.Schedule(class_id=class2.id, weekday=(now.weekday() + 1) % 7,
                                start_time=sched_start, end_time=sched_end, room="P102")
    db.add_all([schedule1, schedule2])
    db.commit()

    return {
        "class1_id": class1.id, "class2_id": class2.id,
        "schedule1_id": schedule1.id, "schedule2_id": schedule2.id,
        "sv1_id": sv1.id, "sv2_id": sv2.id,
    }


def login(client, email, password):
    resp = client.post("/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
