from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import PageBlock, PageBlockType


def _create_page(client: TestClient) -> dict:
    response = client.post(
        "/pages/",
        data={"title": "Página do fórum", "status": "published", "tag_ids": ""},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    return next(page for page in client.get("/pages/").json() if page["title"] == "Página do fórum")


def test_dashboard_prepares_general_discussion_from_forum_link(client: TestClient, register_and_login):
    register_and_login()
    page = _create_page(client)

    response = client.get("/dashboard", params={"open_page": page["id"], "discussion": "page"})
    assert response.status_code == 200
    assert 'data-open-discussion="page"' in response.text
    assert "htmx.ajax('GET'" in response.text


def test_dashboard_prepares_block_discussion_from_forum_link(
    client: TestClient,
    session: Session,
    register_and_login,
):
    register_and_login()
    page = _create_page(client)
    block = PageBlock(page_id=page["id"], block_type=PageBlockType.TEXT, content="Bloco")
    session.add(block)
    session.commit()
    session.refresh(block)

    response = client.get(
        "/dashboard",
        params={"open_page": page["id"], "discussion": f"block-{block.id}"},
    )
    assert response.status_code == 200
    assert f'data-open-discussion="block-{block.id}"' in response.text


def test_dashboard_ignores_invalid_discussion_parameter(client: TestClient, register_and_login):
    register_and_login()
    page = _create_page(client)

    response = client.get("/dashboard", params={"open_page": page["id"], "discussion": "invalid"})
    assert response.status_code == 200
    assert 'data-open-discussion=""' in response.text
