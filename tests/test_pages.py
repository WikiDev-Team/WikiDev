from __future__ import annotations

from fastapi.testclient import TestClient


def test_add_page_without_authentication_returns_401(client: TestClient):
    response = client.post(
        "/pages/",
        data={
            "title": "Página invasora",
            "summary": "Tentando burlar a segurança",
            "page_type": "note",
            "status": "draft",
            "tag_ids": "",
        },
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Não autenticado"}


def test_add_page_with_authentication_succeeds(
    client: TestClient,
    register_and_login,
):
    register_and_login(
        username="escritor",
        email="escritor@wiki.com",
        display_name="O Escritor",
    )
    response = client.post(
        "/pages/",
        data={
            "title": "Minha Primeira Página Protegida",
            "summary": "Resumo da página HTMX",
            "page_type": "note",
            "status": "draft",
            "tag_ids": "",
        },
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    assert "Minha Primeira Página Protegida" in response.text
