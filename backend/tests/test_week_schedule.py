"""Test GET /schedules/week: gop lich hoc/day theo tuan voi trang thai phien/diem danh."""
from datetime import date, timedelta

from tests.conftest import auth_headers, login


def _this_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())


def test_week_schedule_student_sees_own_class_and_manual_status(client, seed):
    # schedule1 duoc seed vao thu cua NGAY HOM NAY (open_session chi cho mo hom nay)
    monday = _this_monday()
    today = date.today()
    gv_token = login(client, "gv1@test.local", "gv123")
    open_resp = client.post(
        "/sessions", json={"schedule_id": seed["schedule1_id"], "session_date": str(today)},
        headers=auth_headers(gv_token),
    )
    session_id = open_resp.json()["id"]
    client.post(f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
               headers=auth_headers(gv_token))

    sv_token = login(client, "sv1@test.local", "sv123")
    resp = client.get("/schedules/week", params={"start": str(monday)}, headers=auth_headers(sv_token))
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["class_code"] == "C1"
    assert entry["date"] == str(today)
    assert entry["session_status"] == "open"
    assert entry["my_status"] == "manual"


def test_week_schedule_lecturer_sees_present_count_after_close(client, seed):
    monday = _this_monday()
    gv_token = login(client, "gv1@test.local", "gv123")
    open_resp = client.post(
        "/sessions", json={"schedule_id": seed["schedule1_id"], "session_date": str(date.today())},
        headers=auth_headers(gv_token),
    )
    session_id = open_resp.json()["id"]
    client.post(f"/sessions/{session_id}/manual", json={"student_id": seed["sv1_id"]},
               headers=auth_headers(gv_token))
    client.patch(f"/sessions/{session_id}/close", headers=auth_headers(gv_token))

    resp = client.get("/schedules/week", params={"start": str(monday)}, headers=auth_headers(gv_token))
    assert resp.status_code == 200
    entry = resp.json()[0]
    assert entry["session_status"] == "closed"
    assert entry["present_count"] == 1  # sv1 duoc xac nhan tay -> tinh la co mat
    assert entry["total_count"] == 1    # chi sv1 ghi danh lop C1


def test_week_schedule_slot_with_no_session_yet_has_null_status(client, seed):
    monday = _this_monday()
    sv_token = login(client, "sv1@test.local", "sv123")
    resp = client.get("/schedules/week", params={"start": str(monday)}, headers=auth_headers(sv_token))
    assert resp.status_code == 200
    entry = resp.json()[0]
    assert entry["session_id"] is None
    assert entry["session_status"] is None
    assert entry["my_status"] is None


def test_week_schedule_other_lecturer_does_not_see_class_not_theirs(client, seed):
    monday = _this_monday()
    gv2_token = login(client, "gv2@test.local", "gv123")
    resp = client.get("/schedules/week", params={"start": str(monday)}, headers=auth_headers(gv2_token))
    assert resp.status_code == 200
    class_codes = {e["class_code"] for e in resp.json()}
    assert "C1" not in class_codes


def test_week_schedule_normalizes_non_monday_start_to_that_week(client, seed):
    monday = _this_monday()
    mid_week = monday + timedelta(days=3)  # Thu 5 cung tuan
    sv_token = login(client, "sv1@test.local", "sv123")
    resp = client.get("/schedules/week", params={"start": str(mid_week)}, headers=auth_headers(sv_token))
    assert resp.status_code == 200
    entry = resp.json()[0]
    # van tra ve dung ngay cua slot trong tuan chua ngay duoc truyen vao
    # (schedule1 nam o thu cua hom nay - xem fixture seed)
    assert entry["date"] == str(date.today())
