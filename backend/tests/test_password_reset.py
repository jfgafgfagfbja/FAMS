"""Test luong quen mat khau bang OTP: gui email (khong lo email), dat lai mat khau
(OTP sai/het han/da dung deu bi tu choi), va thu hoi token cu sau khi doi mat khau."""
from datetime import datetime, timedelta

from app.core.security import hash_password
from app.db import models
from tests.conftest import auth_headers, login


def _user_id(db_session, email):
    return db_session.query(models.User).filter_by(email=email).first().id


def _create_reset(db_session, user_id, otp="111111", expires_delta=timedelta(minutes=10), used=False):
    reset = models.PasswordReset(
        user_id=user_id, otp_hash=hash_password(otp),
        expires_at=datetime.utcnow() + expires_delta, used=used,
    )
    db_session.add(reset)
    db_session.commit()
    return reset


def test_forgot_password_returns_generic_message_for_existing_email(client, seed):
    resp = client.post("/auth/forgot-password", json={"email": "sv1@test.local"})
    assert resp.status_code == 200
    assert "OTP" in resp.json()["message"]


def test_forgot_password_returns_same_generic_message_for_unknown_email(client, seed):
    resp_known = client.post("/auth/forgot-password", json={"email": "sv1@test.local"})
    resp_unknown = client.post("/auth/forgot-password", json={"email": "khong-ton-tai@test.local"})
    assert resp_known.status_code == resp_unknown.status_code == 200
    assert resp_known.json() == resp_unknown.json()


def test_forgot_password_creates_hashed_reset_row(client, seed, db_session):
    client.post("/auth/forgot-password", json={"email": "sv1@test.local"})
    row = db_session.query(models.PasswordReset).filter_by(user_id=_user_id(db_session, "sv1@test.local")).first()
    assert row is not None
    assert row.used is False
    assert row.otp_hash and not row.otp_hash.isdigit()  # da bam, khong luu OTP tho 6 so


def test_forgot_password_rate_limited_after_3_per_hour(client, seed):
    for _ in range(3):
        resp = client.post("/auth/forgot-password", json={"email": "sv1@test.local"})
        assert resp.status_code == 200
    resp = client.post("/auth/forgot-password", json={"email": "sv1@test.local"})
    assert resp.status_code == 429


def test_reset_password_wrong_otp_rejected(client, seed, db_session):
    _create_reset(db_session, _user_id(db_session, "sv1@test.local"), otp="111111")
    resp = client.post("/auth/reset-password", json={
        "email": "sv1@test.local", "otp": "999999", "new_password": "matkhaumoi123",
    })
    assert resp.status_code == 400


def test_reset_password_expired_otp_rejected(client, seed, db_session):
    _create_reset(db_session, _user_id(db_session, "sv1@test.local"), otp="111111", expires_delta=timedelta(minutes=-1))
    resp = client.post("/auth/reset-password", json={
        "email": "sv1@test.local", "otp": "111111", "new_password": "matkhaumoi123",
    })
    assert resp.status_code == 400


def test_reset_password_already_used_otp_rejected(client, seed, db_session):
    _create_reset(db_session, _user_id(db_session, "sv1@test.local"), otp="111111", used=True)
    resp = client.post("/auth/reset-password", json={
        "email": "sv1@test.local", "otp": "111111", "new_password": "matkhaumoi123",
    })
    assert resp.status_code == 400


def test_reset_password_rejects_password_shorter_than_8_chars(client, seed, db_session):
    _create_reset(db_session, _user_id(db_session, "sv1@test.local"), otp="111111")
    resp = client.post("/auth/reset-password", json={
        "email": "sv1@test.local", "otp": "111111", "new_password": "short",
    })
    assert resp.status_code == 422


def test_reset_password_unknown_email_rejected(client, seed):
    resp = client.post("/auth/reset-password", json={
        "email": "khong-ton-tai@test.local", "otp": "111111", "new_password": "matkhaumoi123",
    })
    assert resp.status_code == 400


def test_reset_password_success_changes_password(client, seed, db_session):
    _create_reset(db_session, _user_id(db_session, "sv1@test.local"), otp="111111")
    resp = client.post("/auth/reset-password", json={
        "email": "sv1@test.local", "otp": "111111", "new_password": "matkhaumoi123",
    })
    assert resp.status_code == 200

    old_login = client.post("/auth/login", data={"username": "sv1@test.local", "password": "sv123"})
    assert old_login.status_code == 401

    new_login = client.post("/auth/login", data={"username": "sv1@test.local", "password": "matkhaumoi123"})
    assert new_login.status_code == 200


def test_reset_password_otp_cannot_be_reused(client, seed, db_session):
    _create_reset(db_session, _user_id(db_session, "sv1@test.local"), otp="111111")
    first = client.post("/auth/reset-password", json={
        "email": "sv1@test.local", "otp": "111111", "new_password": "matkhaumoi123",
    })
    assert first.status_code == 200

    second = client.post("/auth/reset-password", json={
        "email": "sv1@test.local", "otp": "111111", "new_password": "khacmatkhau456",
    })
    assert second.status_code == 400


def test_reset_password_revokes_previously_issued_tokens(client, seed, db_session):
    old_token = login(client, "sv1@test.local", "sv123")
    still_valid = client.get("/students/me", headers=auth_headers(old_token))
    assert still_valid.status_code == 200

    _create_reset(db_session, _user_id(db_session, "sv1@test.local"), otp="111111")
    reset_resp = client.post("/auth/reset-password", json={
        "email": "sv1@test.local", "otp": "111111", "new_password": "matkhaumoi123",
    })
    assert reset_resp.status_code == 200

    after_reset = client.get("/students/me", headers=auth_headers(old_token))
    assert after_reset.status_code == 401

    new_token = login(client, "sv1@test.local", "matkhaumoi123")
    fresh = client.get("/students/me", headers=auth_headers(new_token))
    assert fresh.status_code == 200
