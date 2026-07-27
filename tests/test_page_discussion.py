from __future__ import annotations

from fastapi.testclient import TestClient


def _logout(client: TestClient) -> None:
    client.post("/logout")


def _create_public_page(client: TestClient) -> dict:
    folder = client.post(
        "/folders/",
        json={"name": "Discussões públicas", "visibility": "public"},
    ).json()
    response = client.post(
        f"/folders/{folder['id']}/pages",
        json={"title": "Página discutida", "status": "published", "tag_ids": []},
    )
    assert response.status_code == 201
    return response.json()


def test_discussion_starts_collapsed_and_loads_on_demand(client: TestClient, register_and_login):
    register_and_login()
    page = _create_public_page(client)

    editor = client.get(f"/pages/{page['id']}/blocks-editor")
    assert editor.status_code == 200
    assert f"/comments/pages/{page['id']}/discussion" in editor.text
    assert 'hx-trigger="toggle once"' in editor.text
    assert "new-comment-form" not in editor.text

    discussion = client.get(f"/comments/pages/{page['id']}/discussion", headers={"HX-Request": "true"})
    assert discussion.status_code == 200
    assert "+ Adicionar comentário" in discussion.text
    assert 'class="new-comment-form" hidden' in discussion.text
    assert 'class="comment-code-fields" hidden' in discussion.text


def test_page_discussion_creates_and_escapes_comment_html(client: TestClient, register_and_login):
    register_and_login()
    page = _create_public_page(client)

    response = client.post(
        f"/comments/pages/{page['id']}/discussion",
        data={"body": "<script>alert('texto')</script>", "code": "", "language": ""},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 201
    assert "&lt;script&gt;alert" in response.text
    assert "<script>alert" not in response.text


def test_page_discussion_supports_reply_edit_and_remove(client: TestClient, register_and_login):
    register_and_login()
    page = _create_public_page(client)
    created = client.post(
        f"/comments/pages/{page['id']}/discussion",
        data={"body": "Comentário original", "code": "", "language": ""},
        headers={"HX-Request": "true"},
    )
    assert created.status_code == 201
    comment = client.get("/comments/", params={"page_id": page["id"]}).json()[0]

    reply_form = client.get(f"/comments/{comment['id']}/reply-form", headers={"HX-Request": "true"})
    assert reply_form.status_code == 200
    assert "Respondendo a @ada" in reply_form.text
    reply = client.post(
        f"/comments/{comment['id']}/replies",
        data={"body": "Resposta", "code": "", "language": ""},
        headers={"HX-Request": "true"},
    )
    assert reply.status_code == 201
    assert "Resposta" in reply.text

    edited = client.patch(
        f"/comments/{comment['id']}/discussion",
        data={"body": "Comentário editado", "code": "", "language": ""},
        headers={"HX-Request": "true"},
    )
    assert edited.status_code == 200
    assert "Comentário editado" in edited.text
    removed = client.delete(
        f"/comments/{comment['id']}/discussion",
        headers={"HX-Request": "true"},
    )
    assert removed.status_code == 200
    assert "Comentário removido" in removed.text
    assert "Resposta" in removed.text


def test_only_author_can_edit_or_remove_discussion_comment(client: TestClient, register_and_login):
    register_and_login(username="owner", email="owner@example.com")
    page = _create_public_page(client)
    client.post(
        f"/comments/pages/{page['id']}/discussion",
        data={"body": "Comentário do autor", "code": "", "language": ""},
        headers={"HX-Request": "true"},
    )
    comment = client.get("/comments/", params={"page_id": page["id"]}).json()[0]

    _logout(client)
    register_and_login(username="reader", email="reader@example.com")
    assert client.get(f"/comments/{comment['id']}/edit-form", headers={"HX-Request": "true"}).status_code == 403
    assert client.delete(f"/comments/{comment['id']}/discussion", headers={"HX-Request": "true"}).status_code == 403


def test_private_page_discussion_is_not_exposed(client: TestClient, register_and_login):
    register_and_login(username="owner", email="owner@example.com")
    private_folder = client.post("/folders/", json={"name": "Privada"}).json()
    page = client.post(
        f"/folders/{private_folder['id']}/pages",
        json={"title": "Página privada", "status": "published", "tag_ids": []},
    ).json()

    _logout(client)
    register_and_login(username="reader", email="reader@example.com")
    response = client.get(f"/comments/pages/{page['id']}/discussion", headers={"HX-Request": "true"})
    assert response.status_code == 404
