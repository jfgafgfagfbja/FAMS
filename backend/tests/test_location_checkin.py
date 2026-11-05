"""Doi chieu GPS khi SV tu diem danh bang selfie voi dia diem cua lich hoc."""
from datetime import date

import pytest

from app.core.config import settings
from app.core.security import hash_password
from app.db import models
from app.services import face_service
from app.services.geo_service import haversine_m
from tests.conftest import auth_headers, login

CAMPUS = (16.0320, 108.2210)
# ~111 m moi 0.001 do vi do.
NEAR = (16.0325, 108.2210)      # ~55 m
FAR = (16.0420, 108.2210)       # ~1.1 km


@pytest.fixture()
def open_session(client, db_session, seed):
    token = login(client, "gv1@test.local", "gv123")
    resp = client.post("/sessions", json={"schedule_id": seed["schedule1_id"],
                                          "session_date": str(date.today())},
                       headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


@pytest.fixture()
def campus(db_session, seed):
    location = models.Location(code="CS1", name="Co so chinh", latitude=CAMPUS[0],
                               longitude=CAMPUS[1], radius_m=150, is_default=True)
    db_session.add(location)
    db_session.commit()
    return location


@pytest.fixture()
def matched_face(monkeypatch, db_session, seed):
    """Khuon mat SV1 khop. Ngoai doi chi khop duoc khi SV da dong y va dang ky khuon mat."""
    db_session.get(models.Student, seed["sv1_id"]).consent_given = True
    db_session.commit()
    monkeypatch.setattr(face_service, "recognize_self", lambda db, data, student_id: {
        "status": "matched", "confidence": 0.91, "liveness_score": 0.9, "bbox": [0, 0, 10, 10]})


def _checkin(client, session_id, **fields):
    token = login(client, "sv1@test.local", "sv123")
    data = {k: str(v) for k, v in fields.items() if v is not None}
    return client.post(f"/sessions/{session_id}/self-checkin", data=data,
                       files={"frame": ("f.jpg", b"x", "image/jpeg")}, headers=auth_headers(token))


def test_haversine_distance():
    assert haversine_m(*CAMPUS, *CAMPUS) == 0
    assert 50 < haversine_m(*CAMPUS, *NEAR) < 60
    assert 1000 < haversine_m(*CAMPUS, *FAR) < 1200


def test_checkin_inside_radius_records_distance(client, open_session, campus, matched_face):
    resp = _checkin(client, open_session, latitude=NEAR[0], longitude=NEAR[1], accuracy=20)
    body = resp.json()
    assert body["status"] == "recognized", body
    assert 50 < body["distance_m"] < 60
    assert body["allowed_radius_m"] == 150

    token = login(client, "gv1@test.local", "gv123")
    roster = client.get(f"/sessions/{open_session}/roster", headers=auth_headers(token)).json()
    entry = next(r for r in roster if r["status"])
    assert 50 < entry["distance_m"] < 60


def test_checkin_outside_radius_rejected(client, open_session, campus, matched_face):
    body = _checkin(client, open_session, latitude=FAR[0], longitude=FAR[1], accuracy=15).json()
    assert body["status"] == "out_of_range"
    assert body["distance_m"] > 1000
    token = login(client, "gv1@test.local", "gv123")
    records = client.get(f"/sessions/{open_session}/records", headers=auth_headers(token)).json()
    assert records == []


def test_accuracy_counts_in_student_favor(client, open_session, campus, matched_face):
    """Cach ~200 m nhung sai so 80 m -> 200 - 80 = 120 <= 150: chap nhan."""
    body = _checkin(client, open_session, latitude=16.0338, longitude=108.2210, accuracy=80).json()
    assert body["status"] == "recognized", body


def test_missing_location_rejected(client, open_session, campus, matched_face):
    assert _checkin(client, open_session).json()["status"] == "location_required"


def test_inaccurate_location_rejected(client, open_session, campus, matched_face):
    body = _checkin(client, open_session, latitude=NEAR[0], longitude=NEAR[1], accuracy=500).json()
    assert body["status"] == "location_inaccurate"


def test_mocked_location_rejected(client, open_session, campus, matched_face):
    body = _checkin(client, open_session, latitude=NEAR[0], longitude=NEAR[1], accuracy=10,
                    is_mocked="true").json()
    assert body["status"] == "location_mocked"


def test_no_location_configured_skips_check(client, open_session, matched_face):
    assert _checkin(client, open_session).json()["status"] == "recognized"


def test_check_can_be_disabled(client, open_session, campus, matched_face, monkeypatch):
    monkeypatch.setattr(settings, "SELF_CHECKIN_REQUIRE_LOCATION", False)
    assert _checkin(client, open_session).json()["status"] == "recognized"


def test_schedule_specific_location_overrides_default(client, db_session, seed, open_session, campus,
                                                       matched_face):
    other = models.Location(code="CS2", name="Co so 2", latitude=FAR[0], longitude=FAR[1], radius_m=100)
    db_session.add(other)
    db_session.flush()
    db_session.get(models.Schedule, seed["schedule1_id"]).location_id = other.id
    db_session.commit()
    body = _checkin(client, open_session, latitude=FAR[0], longitude=FAR[1], accuracy=10).json()
    assert body["status"] == "recognized", body


# ---------------- API dia diem ----------------

def test_training_office_manages_locations_single_default(client, db_session, seed):
    pdt_user = models.User(email="pdt@test.local", role="training_office", full_name="PDT",
                           password_hash=hash_password("pdt12345"))
    unit = models.Unit(code="P-DT", name="Phong Dao tao", type="training")
    db_session.add_all([pdt_user, unit])
    db_session.flush()
    db_session.add(models.Staff(user_id=pdt_user.id, unit_id=unit.id))
    db_session.commit()
    h = auth_headers(login(client, "pdt@test.local", "pdt12345"))

    first = client.post("/locations", json={"code": "A", "name": "A", "latitude": 16.03,
                                            "longitude": 108.22, "is_default": True}, headers=h).json()
    second = client.post("/locations", json={"code": "B", "name": "B", "latitude": 16.04,
                                             "longitude": 108.23, "radius_m": 200, "is_default": True},
                         headers=h).json()
    listed = {l["code"]: l for l in client.get("/locations", headers=h).json()}
    assert listed["B"]["is_default"] is True
    assert listed["A"]["is_default"] is False

    bad = client.post("/locations", json={"code": "C", "name": "C", "latitude": 100, "longitude": 0},
                      headers=h)
    assert bad.status_code == 422

    resp = client.patch(f"/classes/schedules/{seed['schedule1_id']}", json={"location_id": second["id"]},
                        headers=h)
    assert resp.status_code == 200 and resp.json()["location_id"] == second["id"]
    assert client.delete(f"/locations/{second['id']}", headers=h).status_code == 409
    assert client.delete(f"/locations/{first['id']}", headers=h).status_code == 200


def test_students_cannot_manage_locations(client, seed):
    h = auth_headers(login(client, "sv1@test.local", "sv123"))
    assert client.get("/locations", headers=h).status_code == 403
    assert client.post("/locations", json={"code": "X", "name": "X", "latitude": 1, "longitude": 1},
                       headers=h).status_code == 403


def test_week_schedule_shows_effective_location(client, campus, seed):
    h = auth_headers(login(client, "sv1@test.local", "sv123"))
    slots = client.get("/schedules/week", headers=h).json()
    assert slots and slots[0]["location_name"] == "Co so chinh"
    assert slots[0]["location_radius_m"] == 150
