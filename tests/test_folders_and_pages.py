from __future__ import annotations

from fastapi.testclient import TestClient


def _logout(client: TestClient) -> None:
    client.post("/logout")


def test_folder_page_context_privacy_and_author_spoofing(client: TestClient, register_and_login):
    register_and_login(username="owner", email="owner@example.com")

    folder_response = client.post(
        "/folders/",
        json={
            "name": "Arquitetura",
            "description": "Decisões internas",
            "visibility": "private",
            "author_id": 9999,
        },
    )
    assert folder_response.status_code == 201
    folder = folder_response.json()
    assert folder["author_id"] != 9999

    page_response = client.post(
        f"/folders/{folder['id']}/pages",
        json={
            "title": "ADR 001",
            "summary": "Escolha do banco",
            "status": "published",
            "author_id": 9999,
            "tag_ids": [],
        },
    )
    assert page_response.status_code == 201
    page = page_response.json()
    assert page["folder_id"] == folder["id"]
    assert page["author_id"] == folder["author_id"]

    _logout(client)
    register_and_login(username="reader", email="reader@example.com")
    assert client.get(f"/folders/{folder['id']}").status_code == 403
    assert client.get(f"/pages/{page['id']}").status_code == 403

    _logout(client)
    login_owner = client.post(
        "/login",
        data={"username": "owner", "password": "senha-segura"},
        headers={"HX-Request": "true"},
    )
    assert login_owner.status_code == 200
    changed = client.patch(f"/folders/{folder['id']}", json={"visibility": "public"})
    assert changed.status_code == 200

    _logout(client)
    client.post(
        "/login",
        data={"username": "reader", "password": "senha-segura"},
        headers={"HX-Request": "true"},
    )
    assert client.get(f"/folders/{folder['id']}").status_code == 200
    assert client.get(f"/pages/{page['id']}").status_code == 200


def test_attach_detach_existing_page_and_prevent_folder_cycles(client: TestClient, register_and_login):
    register_and_login()
    root = client.post("/folders/", json={"name": "Raiz"}).json()
    child = client.post(
        "/folders/",
        json={"name": "Filha", "parent_folder_id": root["id"]},
    ).json()

    cycle = client.patch(
        f"/folders/{root['id']}",
        json={"parent_folder_id": child["id"]},
    )
    assert cycle.status_code == 422

    loose_page = client.post(
        "/pages/",
        data={
            "title": "Página solta",
            "summary": "",
            "page_type": "note",
            "status": "draft",
            "folder_id": "",
            "tag_ids": "",
        },
        headers={"HX-Request": "true"},
    )
    assert loose_page.status_code == 200

    pages = client.get("/pages/").json()
    page_id = next(page["id"] for page in pages if page["title"] == "Página solta")
    attached = client.put(f"/folders/{root['id']}/pages/{page_id}")
    assert attached.status_code == 200
    assert attached.json()["folder_id"] == root["id"]

    detached = client.delete(f"/folders/{root['id']}/pages/{page_id}")
    assert detached.status_code == 204
    assert client.get(f"/pages/{page_id}").json()["folder_id"] is None


def test_page_metadata_can_remove_page_from_folder(client: TestClient, register_and_login):
    register_and_login()
    folder = client.post("/folders/", json={"name": "Pasta temporária"}).json()
    page = client.post(
        f"/folders/{folder['id']}/pages",
        json={"title": "Página para desvincular", "tag_ids": []},
    ).json()

    response = client.patch(
        f"/pages/{page['id']}",
        data={
            "title": page["title"],
            "summary": "",
            "page_type": page["page_type"],
            "status": page["status"],
            "visibility": page["visibility"],
            "edit_policy": page["edit_policy"],
            "folder_id": "",
        },
    )

    assert response.status_code == 200
    assert client.get(f"/pages/{page['id']}").json()["folder_id"] is None
    assert "Pasta: Pasta temporária" not in response.text


def test_non_owner_cannot_modify_page_folder_or_blocks(client: TestClient, register_and_login):
    register_and_login(username="owner", email="owner@example.com")
    folder = client.post("/folders/", json={"name": "Pública", "visibility": "public"}).json()
    page = client.post(
        f"/folders/{folder['id']}/pages",
        json={"title": "Conteúdo", "status": "published", "tag_ids": []},
    ).json()

    _logout(client)
    register_and_login(username="intruder", email="intruder@example.com")
    assert client.patch(f"/folders/{folder['id']}", json={"name": "Invadida"}).status_code == 403
    assert client.post(
        f"/pages/{page['id']}/blocks",
        data={"block_type": "text"},
    ).status_code == 403
    assert client.delete(f"/pages/{page['id']}").status_code == 403


def test_public_child_does_not_bypass_private_ancestor(client: TestClient, register_and_login):
    register_and_login(username="owner", email="owner@example.com")
    private_root = client.post("/folders/", json={"name": "Raiz privada"}).json()
    public_child = client.post(
        "/folders/",
        json={
            "name": "Filha pública",
            "visibility": "public",
            "parent_folder_id": private_root["id"],
        },
    ).json()
    page = client.post(
        f"/folders/{public_child['id']}/pages",
        json={"title": "Não deve vazar", "status": "published", "tag_ids": []},
    ).json()

    _logout(client)
    register_and_login(username="reader", email="reader@example.com")
    assert client.get(f"/folders/{public_child['id']}").status_code == 403
    assert client.get(f"/pages/{page['id']}").status_code == 403
