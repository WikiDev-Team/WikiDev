from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlmodel import Session, select

import app.routers.auth as auth_module
from app.models import PasswordResetToken, User
from app.security import hash_token


def test_registration_login_logout_and_dev_login_guard(client: TestClient, engine, register_and_login):
    register_and_login()

    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert "Ada" in dashboard.text

    raw_cookie = client.cookies.get("session_token")
    with Session(engine) as db_session:
        user = db_session.exec(select(User).where(User.username == "ada")).one()
        assert user.token == hash_token(raw_cookie)
        assert user.token != raw_cookie

    logout = client.post("/logout", headers={"HX-Request": "true"})
    assert logout.status_code == 200
    assert logout.headers["HX-Redirect"] == "/login"
    assert "session_token" not in client.cookies
    assert client.get("/dev-login").status_code == 404


def test_duplicate_registration_does_not_leak_or_overwrite(client: TestClient, register_and_login):
    register_and_login()
    response = client.post(
        "/register",
        data={
            "username": "ada",
            "email": "other@example.com",
            "password": "outra-senha",
            "password_confirm": "outra-senha",
        },
    )
    assert response.status_code == 200
    assert "já cadastrado" in response.text


def test_password_reset_is_hashed_expiring_and_single_use(
    client: TestClient,
    engine,
    register_and_login,
    monkeypatch,
):
    register_and_login(password="senha-antiga")
    client.post("/logout")

    sent: dict[str, str] = {}

    def fake_send_password_reset_email(*, to_email, username, reset_url, settings):
        sent.update(to_email=to_email, username=username, reset_url=reset_url)

    monkeypatch.setattr(auth_module, "send_password_reset_email", fake_send_password_reset_email)

    response = client.post("/forgot-password", data={"email": "ada@example.com"})
    assert response.status_code == 200
    assert "Se o e-mail estiver cadastrado" in response.text
    assert sent["to_email"] == "ada@example.com"

    raw_token = parse_qs(urlparse(sent["reset_url"]).query)["token"][0]
    with Session(engine) as db_session:
        stored = db_session.exec(select(PasswordResetToken)).one()
        assert stored.token_hash == hash_token(raw_token)
        assert stored.token_hash != raw_token
        assert stored.used_at is None

    reset = client.post(
        "/reset-password",
        data={
            "token": raw_token,
            "password": "senha-nova",
            "password_confirm": "senha-nova",
        },
        headers={"HX-Request": "true"},
    )
    assert reset.status_code == 200
    assert reset.headers["HX-Redirect"] == "/login?reset=1"

    reused = client.post(
        "/reset-password",
        data={
            "token": raw_token,
            "password": "terceira-senha",
            "password_confirm": "terceira-senha",
        },
    )
    assert "inválido ou expirou" in reused.text

    old_login = client.post("/login", data={"username": "ada", "password": "senha-antiga"})
    assert "inválidos" in old_login.text
    new_login = client.post(
        "/login",
        data={"username": "ada", "password": "senha-nova"},
        headers={"HX-Request": "true"},
    )
    assert new_login.headers["HX-Redirect"] == "/dashboard"

    with Session(engine) as db_session:
        user = db_session.exec(select(User).where(User.username == "ada")).one()
        assert user.hashed_password != "senha-nova"


def test_forgot_password_response_does_not_enumerate_accounts(client: TestClient):
    response = client.post("/forgot-password", data={"email": "unknown@example.com"})
    assert response.status_code == 200
    assert "Se o e-mail estiver cadastrado" in response.text
