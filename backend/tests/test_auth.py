from tests.conftest import auth_headers, login


def test_login_success(client, seed):
    token = login(client, "admin@test.local", "admin123")
    assert token


def test_login_wrong_password(client, seed):
    resp = client.post("/auth/login", data={"username": "admin@test.local", "password": "wrong"})
    assert resp.status_code == 401


def test_login_rate_limited_after_five_attempts(client, seed):
    for _ in range(5):
        resp = client.post("/auth/login", data={"username": "admin@test.local", "password": "wrong"})
        assert resp.status_code == 401
    resp = client.post("/auth/login", data={"username": "admin@test.local", "password": "wrong"})
    assert resp.status_code == 429


def test_logout_revokes_token(client, seed):
    token = login(client, "admin@test.local", "admin123")
    ok = client.get("/students", headers=auth_headers(token))
    assert ok.status_code == 200

    logout_resp = client.post("/auth/logout", headers=auth_headers(token))
    assert logout_resp.status_code == 200

    after = client.get("/students", headers=auth_headers(token))
    assert after.status_code == 401
