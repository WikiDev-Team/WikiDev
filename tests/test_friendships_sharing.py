from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.crud import create_user
from app.models import (
    FolderShare,
    Friendship,
    FriendshipStatus,
    Page,
    PageShare,
    PageSharePermission,
    UserCreate,
)
from app.security import generate_session_token, hash_token


def _create_authenticated_user(client: TestClient, engine, username: str):
    raw_token = generate_session_token()
    with Session(engine) as session:
        user = create_user(
            session,
            UserCreate(
                username=username,
                email=f"{username}@example.com",
                display_name=username.title(),
                password="secret123",
            ),
        )
        user.token = hash_token(raw_token)
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id
    client.cookies.set("session_token", raw_token)
    return user_id, raw_token


def _login_as(client: TestClient, raw_token: str) -> None:
    client.cookies.set("session_token", raw_token)


def _create_page(
    client: TestClient,
    title: str,
    visibility: str,
    viewers=None,
    editors=None,
    edit_policy="owner",
) -> int:
    response = client.post(
        "/pages/",
        data={
            "title": title,
            "summary": "Página de teste",
            "page_type": "note",
            "status": "draft",
            "visibility": visibility,
            "edit_policy": edit_policy,
            "tag_ids": "",
            "shared_user_ids": [str(value) for value in (viewers or [])],
            "editor_user_ids": [str(value) for value in (editors or [])],
        },
    )
    assert response.status_code == 200, response.text
    pages = client.get("/pages/").json()
    return next(page["id"] for page in pages if page["title"] == title)


def _create_folder(
    client: TestClient,
    name: str,
    visibility: str,
    viewers=None,
    editors=None,
    edit_policy="owner",
    parent_folder_id=None,
) -> int:
    response = client.post(
        "/folders/ui",
        data={
            "name": name,
            "description": "Pasta de teste",
            "visibility": visibility,
            "edit_policy": edit_policy,
            "parent_folder_id": (
                ""
                if parent_folder_id is None
                else str(parent_folder_id)
            ),
            "shared_user_ids": [
                str(value)
                for value in (viewers or [])
            ],
            "editor_user_ids": [
                str(value)
                for value in (editors or [])
            ],
        },
    )

    assert response.status_code == 200, response.text

    folders = client.get("/folders/").json()

    return next(
        folder["id"]
        for folder in folders
        if folder["name"] == name
    )


def test_friend_request_lifecycle(client: TestClient, engine):
    alice_id, alice_token = _create_authenticated_user(client, engine, "alice_friend")
    bob_id, bob_token = _create_authenticated_user(client, engine, "bob_friend")
    charlie_id, charlie_token = _create_authenticated_user(client, engine, "charlie_friend")

    _login_as(client, alice_token)
    response = client.post(
        f"/friendships/request/{charlie_id}",
        data={"return_to": "/friends"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    with Session(engine) as session:
        friendship = session.exec(
            select(Friendship).where(
                (Friendship.requester_id == alice_id)
                & (Friendship.addressee_id == charlie_id)
            )
        ).one()
        friendship_id = friendship.id

    _login_as(client, bob_token)
    assert client.post(
        f"/friendships/{friendship_id}/accept", data={"return_to": "/friends"}
    ).status_code == 403

    _login_as(client, charlie_token)
    assert client.post(
        f"/friendships/{friendship_id}/accept",
        data={"return_to": "/friends"},
        follow_redirects=False,
    ).status_code == 303

    with Session(engine) as session:
        assert session.get(Friendship, friendship_id).status == FriendshipStatus.ACCEPTED


def test_visibility_edit_and_friendship_revocation(client: TestClient, engine):
    alice_id, alice_token = _create_authenticated_user(client, engine, "alice_share")
    bob_id, bob_token = _create_authenticated_user(client, engine, "bob_share")
    charlie_id, charlie_token = _create_authenticated_user(client, engine, "charlie_share")

    with Session(engine) as session:
        friendship = Friendship(
            requester_id=alice_id,
            addressee_id=bob_id,
            status=FriendshipStatus.ACCEPTED,
        )
        session.add(friendship)
        session.commit()
        session.refresh(friendship)
        friendship_id = friendship.id

    _login_as(client, alice_token)
    private_id = _create_page(client, "Private friendship test", "private")
    friends_id = _create_page(client, "Friends friendship test", "friends")
    viewer_id = _create_page(client, "Custom viewer friendship test", "custom", viewers=[bob_id])
    editor_id = _create_page(client, "Custom editor friendship test", "custom", editors=[bob_id])
    public_id = _create_page(client, "Public friendship test", "public")

    _login_as(client, bob_token)
    assert client.get(f"/pages/{private_id}/blocks-editor").status_code == 404
    assert client.get(f"/pages/{friends_id}/blocks-editor").status_code == 200
    viewer_response = client.get(f"/pages/{viewer_id}/blocks-editor")
    assert viewer_response.status_code == 200
    assert "Somente leitura" in viewer_response.text
    assert client.post(f"/pages/{viewer_id}/blocks", data={"block_type": "text"}).status_code == 403

    editor_response = client.get(f"/pages/{editor_id}/blocks-editor")
    assert editor_response.status_code == 200
    assert "Editar página" in editor_response.text
    assert client.post(f"/pages/{editor_id}/blocks", data={"block_type": "text"}).status_code == 200
    assert client.delete(f"/pages/{editor_id}").status_code == 403

    with Session(engine) as session:
        share = session.get(PageShare, (editor_id, bob_id))
        assert share is not None and share.permission == PageSharePermission.EDIT

    _login_as(client, charlie_token)
    assert client.get(f"/pages/{public_id}/blocks-editor").status_code == 200
    assert client.get(f"/pages/{friends_id}/blocks-editor").status_code == 404

    _login_as(client, bob_token)
    removed = client.post(
        f"/friendships/{friendship_id}/remove",
        data={"return_to": f"/profile/{alice_id}"},
        follow_redirects=False,
    )
    assert removed.status_code == 303
    assert client.get(f"/pages/{viewer_id}/blocks-editor").status_code == 404
    with Session(engine) as session:
        assert session.get(Friendship, friendship_id) is None
        assert session.get(PageShare, (viewer_id, bob_id)) is None


def test_public_page_can_be_edited_by_selected_friend(client: TestClient, engine):
    alice_id, alice_token = _create_authenticated_user(client, engine, "alice_public_edit")
    bob_id, bob_token = _create_authenticated_user(client, engine, "bob_public_edit")
    _, charlie_token = _create_authenticated_user(client, engine, "charlie_public_edit")

    with Session(engine) as session:
        session.add(
            Friendship(
                requester_id=alice_id,
                addressee_id=bob_id,
                status=FriendshipStatus.ACCEPTED,
            )
        )
        session.commit()

    _login_as(client, alice_token)
    page_id = _create_page(
        client,
        "Pública com editor selecionado",
        "public",
        editors=[bob_id],
        edit_policy="custom",
    )

    _login_as(client, bob_token)
    assert client.get(f"/pages/{page_id}/blocks-editor").status_code == 200
    assert client.post(f"/pages/{page_id}/blocks", data={"block_type": "text"}).status_code == 200

    _login_as(client, charlie_token)
    assert client.get(f"/pages/{page_id}/blocks-editor").status_code == 200
    assert client.post(f"/pages/{page_id}/blocks", data={"block_type": "text"}).status_code == 403


def test_every_viewer_can_edit_when_page_policy_allows_it(client: TestClient, engine):
    alice_id, alice_token = _create_authenticated_user(client, engine, "alice_viewer_edit")
    bob_id, bob_token = _create_authenticated_user(client, engine, "bob_viewer_edit")

    with Session(engine) as session:
        session.add(
            Friendship(
                requester_id=alice_id,
                addressee_id=bob_id,
                status=FriendshipStatus.ACCEPTED,
            )
        )
        session.commit()

    _login_as(client, alice_token)
    page_id = _create_page(
        client,
        "Amigos podem editar",
        "friends",
        edit_policy="viewers",
    )

    _login_as(client, bob_token)
    assert client.post(f"/pages/{page_id}/blocks", data={"block_type": "text"}).status_code == 200
    
def test_folder_visibility_and_friendship_revocation(client: TestClient, engine):
    alice_id, alice_token = _create_authenticated_user(client, engine, "alice_folder_share")
    bob_id, bob_token = _create_authenticated_user(client, engine, "bob_folder_share")
    _, charlie_token = _create_authenticated_user(client, engine, "charlie_folder_share")

    with Session(engine) as session:
        friendship = Friendship(
            requester_id=alice_id,
            addressee_id=bob_id,
            status=FriendshipStatus.ACCEPTED,
        )
        session.add(friendship)
        session.commit()
        session.refresh(friendship)
        friendship_id = friendship.id

    _login_as(client, alice_token)
    private_id = _create_folder(client, "Private folder test", "private")
    friends_id = _create_folder(client, "Friends folder test", "friends")
    custom_id = _create_folder(client, "Custom folder test", "custom", viewers=[bob_id])
    public_id = _create_folder(client, "Public folder test", "public")

    with Session(engine) as session:
        assert session.get(FolderShare, (custom_id, bob_id)) is not None

    _login_as(client, bob_token)
    assert client.get(f"/folders/{private_id}").status_code == 403
    assert client.get(f"/folders/{friends_id}").status_code == 200
    assert client.get(f"/folders/{custom_id}").status_code == 200
    assert client.get(f"/folders/{public_id}").status_code == 200


    _login_as(client, charlie_token)
    assert client.get(f"/folders/{friends_id}").status_code == 403
    assert client.get(f"/folders/{custom_id}").status_code == 403
    assert client.get(f"/folders/{public_id}").status_code == 200

    _login_as(client, bob_token)
    removed = client.post(
        f"/friendships/{friendship_id}/remove",
        data={"return_to": "/friends"},
        follow_redirects=False,
    )
    assert removed.status_code == 303
    assert client.get(f"/folders/{friends_id}").status_code == 403
    assert client.get(f"/folders/{custom_id}").status_code == 403

    with Session(engine) as session:
        assert session.get(FolderShare, (custom_id, bob_id)) is None


def test_folder_can_be_edited_by_selected_friend(client: TestClient, engine):
    alice_id, alice_token = _create_authenticated_user(client, engine, "alice_folder_edit")
    bob_id, bob_token = _create_authenticated_user(client, engine, "bob_folder_edit")

    with Session(engine) as session:
        session.add(
            Friendship(
                requester_id=alice_id,
                addressee_id=bob_id,
                status=FriendshipStatus.ACCEPTED,
            )
        )
        session.commit()

    _login_as(client, alice_token)
    folder_id = _create_folder(
        client,
        "Pasta com editor",
        "public",
        editors=[bob_id],
        edit_policy="custom",
    )

    _login_as(client, bob_token)
    assert client.post(
        f"/folders/{folder_id}/pages",
        json={"title": "Página do editor", "tag_ids": []},
    ).status_code == 201
    assert client.patch(
        f"/folders/{folder_id}",
        json={"name": "Tentativa de configuração"},
    ).status_code == 403


def test_folder_visibility_respects_parent_folders(client: TestClient, engine):
    alice_id, alice_token = _create_authenticated_user(client, engine, "alice_folder_parent")
    bob_id, bob_token = _create_authenticated_user(client, engine, "bob_folder_parent")

    with Session(engine) as session:
        session.add(
            Friendship(
                requester_id=alice_id,
                addressee_id=bob_id,
                status=FriendshipStatus.ACCEPTED,
            )
        )
        session.commit()

    _login_as(client, alice_token)
    private_parent = _create_folder(client, "Private parent", "private")
    blocked_child = _create_folder(
        client,
        "Shared child under private parent",
        "custom",
        viewers=[bob_id],
        parent_folder_id=private_parent,
    )
    shared_parent = _create_folder(client, "Shared parent", "custom", viewers=[bob_id])
    visible_child = _create_folder(
        client,
        "Public child under shared parent",
        "public",
        parent_folder_id=shared_parent,
    )

    _login_as(client, bob_token)
    assert client.get(f"/folders/{blocked_child}").status_code == 403
    assert client.get(f"/folders/{shared_parent}").status_code == 200
    assert client.get(f"/folders/{visible_child}").status_code == 200


def test_update_folder_without_shared_users(client: TestClient, engine):
    _, alice_token = _create_authenticated_user(client, engine, "alice_folder_update")
    _login_as(client, alice_token)

    folder_id = _create_folder(client, "Folder without shares", "private")
    response = client.patch(
        f"/folders/{folder_id}/ui",
        data={
            "name": "Updated folder",
            "description": "Updated description",
            "visibility": "private",
            "parent_folder_id": "",
        },
    )
    assert response.status_code == 200, response.text


def test_page_sharing_forms_use_one_permission_per_friend(client: TestClient, engine):
    alice_id, alice_token = _create_authenticated_user(client, engine, "alice_sharing_form")
    bob_id, _ = _create_authenticated_user(client, engine, "bob_sharing_form")

    with Session(engine) as session:
        session.add(
            Friendship(
                requester_id=alice_id,
                addressee_id=bob_id,
                status=FriendshipStatus.ACCEPTED,
            )
        )
        session.commit()

    _login_as(client, alice_token)

    create_form = client.get("/pages/new")
    assert create_form.status_code == 200
    assert "data-page-sharing-form" in create_form.text
    assert "data-page-visibility" in create_form.text
    assert "data-page-sharing" in create_form.text
    assert "data-friend-permission" in create_form.text
    assert "Sem acesso" in create_form.text
    assert "Pode visualizar" in create_form.text
    assert "Pode editar" in create_form.text
    assert 'type="checkbox"' not in create_form.text

    page_id = _create_page(client, "Página com compartilhamento", "custom", editors=[bob_id])

    edit_form = client.get(f"/pages/{page_id}/metadata/edit")
    assert edit_form.status_code == 200
    assert "data-page-sharing-form" in edit_form.text
    assert "data-friend-permission" in edit_form.text
    assert 'value="edit"' in edit_form.text
    assert 'type="checkbox"' not in edit_form.text
