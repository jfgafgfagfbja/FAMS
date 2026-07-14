import re
from datetime import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.api.auth import limiter
from app.core.security import hash_password
from app.db import models
from app.db.database import Base, get_db
from app.core.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Login limiter dung storage chung theo process; reset truoc moi test de tranh anh huong cheo."""
    limiter.reset()
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
    schedule1 = models.Schedule(class_id=class1.id, weekday=0, start_time=time(7, 0),
                                end_time=time(9, 0), room="P101")
    schedule2 = models.Schedule(class_id=class2.id, weekday=1, start_time=time(7, 0),
                                end_time=time(9, 0), room="P102")
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
