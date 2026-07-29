from __future__ import annotations

from fastapi.testclient import TestClient


def test_search_returns_only_accessible_pages(client: TestClient, register_and_login):
    register_and_login(username="owner", email="owner@example.com")
    created = client.post(
        "/pages/",
        data={
            "title": "Busca pública de páginas",
            "summary": "Página usada para testar a busca",
            "page_type": "personal",
            "status": "draft",
            "visibility": "public",
            "tag_ids": "",
        },
        headers={"HX-Request": "true"},
    )
    assert created.status_code == 200

    client.post("/logout")
    register_and_login(username="reader", email="reader@example.com")
    response = client.get("/busca", params={"q": "busca"})
    assert response.status_code == 200
    assert "Busca pública de páginas" in response.text
