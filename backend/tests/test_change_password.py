"""Nguoi dung tu doi mat khau trong trang Tai khoan."""
from tests.conftest import auth_headers, login


def _change(client, token, current, new):
    return client.post("/auth/change-password",
                       json={"current_password": current, "new_password": new},
                       headers=auth_headers(token))


def test_change_password_then_login_with_new_one(client, seed):
    token = login(client, "admin@test.local", "admin123")
    resp = _change(client, token, "admin123", "MatKhauMoi#2026")
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]

    new_login = client.post("/auth/login", data={"username": "admin@test.local",
                                                 "password": "MatKhauMoi#2026"})
    assert new_login.status_code == 200
    old_login = client.post("/auth/login", data={"username": "admin@test.local",
                                                 "password": "admin123"})
    assert old_login.status_code == 401


def test_current_session_continues_other_sessions_revoked(client, seed):
    """Phien dang doi nhan token moi va dung tiep; phien cu (may khac) bi dang xuat."""
    other_device = login(client, "gv1@test.local", "gv123")
    this_device = login(client, "gv1@test.local", "gv123")

    resp = _change(client, this_device, "gv123", "GiangVien#2026")
    fresh = resp.json()["access_token"]

    assert client.get("/auth/me", headers=auth_headers(fresh)).status_code == 200
    assert client.get("/auth/me", headers=auth_headers(other_device)).status_code == 401
    assert client.get("/auth/me", headers=auth_headers(this_device)).status_code == 401


def test_old_refresh_tokens_revoked(client, seed):
    first = client.post("/auth/login", data={"username": "sv1@test.local",
                                             "password": "sv123"}).json()
    _change(client, first["access_token"], "sv123", "SinhVien#2026")
    resp = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert resp.status_code == 401


def test_wrong_current_password_rejected(client, seed):
    token = login(client, "admin@test.local", "admin123")
    resp = _change(client, token, "sai-mat-khau", "MatKhauMoi#2026")
    assert resp.status_code == 400
    assert "hien tai khong dung" in resp.json()["detail"]
    # Mat khau cu van dung duoc: doi that bai thi khong duoc thay doi gi.
    assert client.post("/auth/login", data={"username": "admin@test.local",
                                            "password": "admin123"}).status_code == 200


def test_too_short_rejected(client, seed):
    token = login(client, "admin@test.local", "admin123")
    assert _change(client, token, "admin123", "ngan").status_code == 422


def test_same_as_current_rejected(client, seed):
    token = login(client, "admin@test.local", "admin123")
    resp = _change(client, token, "admin123", "admin123")
    assert resp.status_code == 400
    assert "khac mat khau hien tai" in resp.json()["detail"]


def test_repeated_wrong_attempts_locked(client, seed):
    """Chan do mat khau hien tai tu mot phien dang mo san."""
    token = login(client, "admin@test.local", "admin123")
    codes = [_change(client, token, f"sai-{i}", "MatKhauMoi#2026").status_code for i in range(6)]
    assert codes[-1] == 429, codes


def test_requires_login(client, seed):
    resp = client.post("/auth/change-password",
                       json={"current_password": "x", "new_password": "MatKhauMoi#2026"})
    assert resp.status_code == 401
