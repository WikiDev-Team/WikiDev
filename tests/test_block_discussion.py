from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import PageBlock, PageBlockType


def _logout(client: TestClient) -> None:
    client.post("/logout")


def _create_public_page(client: TestClient) -> dict:
    folder = client.post(
        "/folders/",
        json={"name": "Blocos públicos", "visibility": "public"},
    ).json()
    return client.post(
        f"/folders/{folder['id']}/pages",
        json={"title": "Página com blocos", "status": "published", "tag_ids": []},
    ).json()


def _create_block(session: Session, page_id: int, block_type: PageBlockType) -> PageBlock:
    block = PageBlock(page_id=page_id, block_type=block_type, content="Conteúdo do bloco")
    session.add(block)
    session.commit()
    session.refresh(block)
    return block


def test_each_block_has_its_own_collapsed_discussion(
    client: TestClient,
    session: Session,
    register_and_login,
):
    register_and_login()
    page = _create_public_page(client)
    text_block = _create_block(session, page["id"], PageBlockType.TEXT)
    code_block = _create_block(session, page["id"], PageBlockType.CODE)

    editor = client.get(f"/pages/{page['id']}/blocks-editor")
    assert editor.status_code == 200
    assert f"/comments/blocks/{text_block.id}/discussion" in editor.text
    assert f"/comments/blocks/{code_block.id}/discussion" in editor.text
    assert "💬 Comentários" in editor.text


def test_block_discussions_are_isolated_from_page_and_other_blocks(
    client: TestClient,
    session: Session,
    register_and_login,
):
    register_and_login()
    page = _create_public_page(client)
    first_block = _create_block(session, page["id"], PageBlockType.TEXT)
    second_block = _create_block(session, page["id"], PageBlockType.CODE)

    created = client.post(
        f"/comments/blocks/{first_block.id}/discussion",
        data={"body": "Somente no primeiro bloco", "code": "", "language": ""},
        headers={"HX-Request": "true"},
    )
    assert created.status_code == 201
    assert "💬 1 comentário" in created.text

    first_discussion = client.get(f"/comments/blocks/{first_block.id}/discussion")
    second_discussion = client.get(f"/comments/blocks/{second_block.id}/discussion")
    page_discussion = client.get(f"/comments/pages/{page['id']}/discussion")
    assert "Somente no primeiro bloco" in first_discussion.text
    assert "Somente no primeiro bloco" not in second_discussion.text
    assert "Somente no primeiro bloco" not in page_discussion.text


def test_block_comment_supports_reply_edit_remove_and_counter_update(
    client: TestClient,
    session: Session,
    register_and_login,
):
    register_and_login()
    page = _create_public_page(client)
    block = _create_block(session, page["id"], PageBlockType.TEXT)
    client.post(
        f"/comments/blocks/{block.id}/discussion",
        data={"body": "Comentário no bloco", "code": "", "language": ""},
        headers={"HX-Request": "true"},
    )
    comment = client.get("/comments/", params={"page_id": page["id"]}).json()[0]

    reply = client.post(
        f"/comments/{comment['id']}/replies",
        data={"body": "Resposta do bloco", "code": "", "language": ""},
        headers={"HX-Request": "true"},
    )
    assert reply.status_code == 201
    assert "💬 2 comentários" in reply.text

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
    assert "💬 1 comentário" in removed.text


def test_private_block_discussion_is_not_exposed(
    client: TestClient,
    session: Session,
    register_and_login,
):
    register_and_login(username="owner", email="owner@example.com")
    folder = client.post("/folders/", json={"name": "Privada"}).json()
    page = client.post(
        f"/folders/{folder['id']}/pages",
        json={"title": "Página privada", "status": "published", "tag_ids": []},
    ).json()
    block = _create_block(session, page["id"], PageBlockType.TEXT)

    _logout(client)
    register_and_login(username="reader", email="reader@example.com")
    response = client.get(f"/comments/blocks/{block.id}/discussion", headers={"HX-Request": "true"})
    assert response.status_code == 404
