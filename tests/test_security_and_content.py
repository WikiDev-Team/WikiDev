from __future__ import annotations

from fastapi.testclient import TestClient


def _logout(client: TestClient) -> None:
    client.post("/logout")


def test_public_user_api_never_exposes_email(client: TestClient, register_and_login):
    register_and_login()
    me = client.get("/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"

    users = client.get("/users/")
    assert users.status_code == 200
    assert "email" not in users.json()[0]

    public = client.get(f"/users/{users.json()[0]['id']}")
    assert public.status_code == 200
    assert "email" not in public.json()


def test_comment_author_is_server_controlled(client: TestClient, register_and_login):
    register_and_login(username="owner", email="owner@example.com")
    folder = client.post("/folders/", json={"name": "Pública", "visibility": "public"}).json()
    page = client.post(
        f"/folders/{folder['id']}/pages",
        json={"title": "Discussão", "status": "published", "tag_ids": []},
    ).json()
    owner_id = client.get("/users/me").json()["id"]

    _logout(client)
    register_and_login(username="commenter", email="commenter@example.com")
    commenter_id = client.get("/users/me").json()["id"]
    created = client.post(
        "/comments/",
        json={"page_id": page["id"], "author_id": owner_id, "body": "Minha opinião"},
    )
    assert created.status_code == 201
    assert created.json()["author_id"] == commenter_id

    _logout(client)
    client.post(
        "/login",
        data={"username": "owner", "password": "senha-segura"},
        headers={"HX-Request": "true"},
    )
    assert client.patch(
        f"/comments/{created.json()['id']}", json={"body": "alterado"}
    ).status_code == 403


def test_examples_require_page_ownership(client: TestClient, register_and_login):
    register_and_login(username="owner", email="owner@example.com")
    page_html = client.post(
        "/pages/",
        data={"title": "Exemplos", "status": "published", "page_type": "example"},
        headers={"HX-Request": "true"},
    )
    assert page_html.status_code == 200
    page = next(page for page in client.get("/pages/").json() if page["title"] == "Exemplos")

    _logout(client)
    register_and_login(username="reader", email="reader@example.com")
    response = client.post(
        "/examples/",
        json={
            "page_id": page["id"],
            "author_id": 1,
            "title": "Ataque",
            "code": "rm -rf /",
        },
    )
    assert response.status_code == 403


def test_search_respects_private_folder_boundary(client: TestClient, register_and_login):
    register_and_login(username="owner", email="owner@example.com")
    private_folder = client.post("/folders/", json={"name": "Privada"}).json()
    client.post(
        f"/folders/{private_folder['id']}/pages",
        json={"title": "Segredo Absoluto", "status": "published", "tag_ids": []},
    )

    _logout(client)
    register_and_login(username="reader", email="reader@example.com")
    result = client.get("/busca", params={"q": "Segredo"})
    assert result.status_code == 200
    assert "Segredo Absoluto" not in result.text
