"""Proteções adicionadas na revisão de segurança antes da publicação."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Tag
from app.routers.friendships import _safe_return_to


def _login(client: TestClient, username: str, password: str = "senha-segura"):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        headers={"HX-Request": "true"},
    )


def _create_page(client: TestClient, title: str, **fields) -> int:
    data = {"title": title, "visibility": "public", "status": "published", **fields}
    response = client.post("/pages/", data=data, headers={"HX-Request": "true"})
    assert response.status_code == 200
    return next(page["id"] for page in client.get("/pages/").json() if page["title"] == title)


# ── CSRF e cabeçalhos ────────────────────────────────────────────────────────


def test_cross_site_writes_are_rejected(client: TestClient, register_and_login):
    register_and_login()
    page_id = _create_page(client, "Alvo")

    evil = client.delete(f"/pages/{page_id}", headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    null_origin = client.delete(f"/pages/{page_id}", headers={"Origin": "null"})
    assert null_origin.status_code == 403
    evil_referer = client.delete(
        f"/pages/{page_id}", headers={"Referer": "https://evil.example/ataque"}
    )
    assert evil_referer.status_code == 403
    assert client.get(f"/pages/{page_id}").status_code == 200

    same_site = client.delete(f"/pages/{page_id}", headers={"Origin": "http://testserver"})
    assert same_site.status_code == 204


def test_login_from_other_site_is_rejected(client: TestClient, register_and_login):
    register_and_login()
    client.post("/logout")
    response = client.post(
        "/login",
        data={"username": "ada", "password": "senha-segura"},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403


def test_security_headers_are_present(client: TestClient):
    response = client.get("/login")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "connect-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["Referrer-Policy"] == "same-origin"


def test_return_to_rejects_backslash_redirects():
    assert _safe_return_to("/\\evil.example") == "/friends"
    assert _safe_return_to("//evil.example") == "/friends"
    assert _safe_return_to("/profile/2") == "/profile/2"


# ── Força bruta ──────────────────────────────────────────────────────────────


def test_login_is_throttled_after_repeated_failures(client: TestClient, register_and_login):
    register_and_login()
    client.post("/logout")
    for _ in range(10):
        assert "inválidos" in _login(client, "ada", "errada").text
    blocked = _login(client, "ada", "senha-segura")
    assert "Muitas tentativas" in blocked.text
    assert "HX-Redirect" not in blocked.headers

    # Outro usuário não é afetado.
    register_and_login(username="bia", email="bia@example.com")


def test_password_reset_emails_are_rate_limited(client: TestClient, register_and_login, monkeypatch):
    register_and_login()
    sent = []
    monkeypatch.setattr(
        "app.routers.auth.send_password_reset_email", lambda **kwargs: sent.append(kwargs)
    )
    for _ in range(8):
        response = client.post(
            "/forgot-password", data={"email": "ada@example.com"}, headers={"HX-Request": "true"}
        )
        assert "Se o e-mail estiver cadastrado" in response.text
    assert len(sent) == 5


# ── Pastas, tags e linguagens ────────────────────────────────────────────────


def test_folder_editors_cannot_move_other_peoples_pages(client: TestClient, register_and_login):
    # Bia tem uma pasta que qualquer pessoa pode ver e editar.
    register_and_login(username="bia", email="bia@example.com")
    folder = client.post(
        "/folders/",
        json={"name": "Aberta", "visibility": "public", "edit_policy": "viewers"},
    ).json()
    client.post("/logout")

    # Ada publica uma página fora de pastas.
    register_and_login()
    page_id = _create_page(client, "Página da Ada")
    client.post("/logout")

    # Caio pode editar a pasta, mas não pode puxar a página da Ada para ela.
    register_and_login(username="caio", email="caio@example.com")
    assert client.put(f"/folders/{folder['id']}/pages/{page_id}").status_code == 403
    assert client.post(
        f"/folders/{folder['id']}/attach", data={"page_id": page_id}
    ).status_code == 403
    client.post("/logout")

    # A própria Ada pode, e aí Caio não consegue tirá-la da pasta.
    _login(client, "ada")
    assert client.put(f"/folders/{folder['id']}/pages/{page_id}").status_code == 200
    client.post("/logout")
    _login(client, "caio")
    assert client.delete(f"/folders/{folder['id']}/pages/{page_id}").status_code == 403
    client.post("/logout")

    # A dona da pasta pode retirar páginas da própria pasta.
    _login(client, "bia")
    assert client.delete(f"/folders/{folder['id']}/pages/{page_id}").status_code == 204


def test_shared_tags_cannot_be_renamed_by_others(client: TestClient, session: Session, register_and_login):
    register_and_login()
    _create_page(client, "Da Ada", tags="python")
    tag = session.exec(select(Tag).where(Tag.slug == "python")).one()
    client.post("/logout")

    register_and_login(username="bia", email="bia@example.com")
    assert client.patch(f"/tags/{tag.id}", json={"name": "vandalizada"}).status_code == 403

    own = client.post("/tags/", json={"name": "minha"}).json()
    assert client.patch(f"/tags/{own['id']}", json={"name": "minha-renomeada"}).status_code == 200
