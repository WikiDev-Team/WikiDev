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


def test_search_returns_only_accessible_folders(client: TestClient, register_and_login):
    register_and_login(username="folder_owner", email="folder-owner@example.com")
    public_folder = client.post(
        "/folders/",
        json={"name": "Pesquisa pública", "visibility": "public"},
    ).json()
    private_folder = client.post(
        "/folders/",
        json={"name": "Pesquisa privada", "visibility": "private"},
    ).json()
    private_parent = client.post(
        "/folders/",
        json={"name": "Raiz privada", "visibility": "private"},
    ).json()
    blocked_child = client.post(
        "/folders/",
        json={
            "name": "Pesquisa filha pública",
            "visibility": "public",
            "parent_folder_id": private_parent["id"],
        },
    ).json()

    client.post("/logout")
    register_and_login(username="folder_reader", email="folder-reader@example.com")

    response = client.get("/busca", params={"q": "pesquisa"})

    assert response.status_code == 200
    assert "Pastas disponíveis para você" in response.text
    assert "Pesquisa pública" in response.text
    assert f"/dashboard?open_folder={public_folder['id']}" in response.text
    assert "Pesquisa privada" not in response.text
    assert "Pesquisa filha pública" not in response.text

    dashboard = client.get(
        "/dashboard",
        params={"open_folder": public_folder["id"]},
    )
    assert dashboard.status_code == 200
    assert f'hx-get="/folders/{public_folder["id"]}/panel"' in dashboard.text

    blocked_dashboard = client.get(
        "/dashboard",
        params={"open_folder": blocked_child["id"]},
    )
    assert blocked_dashboard.status_code == 200
    assert f'hx-get="/folders/{blocked_child["id"]}/panel"' not in blocked_dashboard.text
