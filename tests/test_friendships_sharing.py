import atexit
import os
import tempfile
import unittest
from pathlib import Path

TEST_DB_PATH = Path(tempfile.gettempdir()) / "wikidev_friendships_test.db"
TEST_DB_PATH.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
atexit.register(lambda: TEST_DB_PATH.unlink(missing_ok=True))

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.crud import create_user
from app.db import engine, init_db
from app.main import app
from app.models import Friendship, FriendshipStatus, Page, PageShare, PageSharePermission, UserCreate


class FriendshipAndSharingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

        with Session(engine) as session:
            cls.alice = create_user(
                session,
                UserCreate(
                    username="alice_friend_test",
                    email="alice_friend_test@example.com",
                    display_name="Alice",
                    password="secret123",
                ),
            )
            cls.bob = create_user(
                session,
                UserCreate(
                    username="bob_friend_test",
                    email="bob_friend_test@example.com",
                    display_name="Bob",
                    password="secret123",
                ),
            )
            cls.charlie = create_user(
                session,
                UserCreate(
                    username="charlie_friend_test",
                    email="charlie_friend_test@example.com",
                    display_name="Charlie",
                    password="secret123",
                ),
            )

            cls.alice.token = "alice-friend-token"
            cls.bob.token = "bob-friend-token"
            cls.charlie.token = "charlie-friend-token"
            session.add(cls.alice)
            session.add(cls.bob)
            session.add(cls.charlie)
            session.commit()
            session.refresh(cls.alice)
            session.refresh(cls.bob)
            session.refresh(cls.charlie)

            session.add(
                Friendship(
                    requester_id=cls.alice.id,
                    addressee_id=cls.bob.id,
                    status=FriendshipStatus.ACCEPTED,
                )
            )
            session.commit()
            session.refresh(cls.alice)
            session.refresh(cls.bob)
            session.refresh(cls.charlie)

            cls.alice_id = cls.alice.id
            cls.bob_id = cls.bob.id
            cls.charlie_id = cls.charlie.id
            cls.alice_token = cls.alice.token
            cls.bob_token = cls.bob.token
            cls.charlie_token = cls.charlie.token

    def login_as(self, token: str):
        self.client.cookies.set("session_token", token)

    def create_page(self, title: str, visibility: str, viewers=None, editors=None) -> int:
        self.login_as(self.alice_token)
        response = self.client.post(
            "/pages/",
            data={
                "title": title,
                "summary": "Página de teste",
                "page_type": "note",
                "status": "draft",
                "visibility": visibility,
                "tag_ids": "",
                "shared_user_ids": [str(value) for value in (viewers or [])],
                "editor_user_ids": [str(value) for value in (editors or [])],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)

        with Session(engine) as session:
            page = session.exec(select(Page).where(Page.title == title)).first()
            self.assertIsNotNone(page)
            return page.id

    def test_01_friend_request_lifecycle(self):
        self.login_as(self.alice_token)
        response = self.client.post(
            f"/friendships/request/{self.charlie_id}",
            data={"return_to": "/friends"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)

        with Session(engine) as session:
            friendship = session.exec(
                select(Friendship).where(
                    (Friendship.requester_id == self.alice_id)
                    & (Friendship.addressee_id == self.charlie_id)
                )
            ).first()
            self.assertIsNotNone(friendship)
            self.assertEqual(friendship.status, FriendshipStatus.PENDING)
            friendship_id = friendship.id

        self.login_as(self.bob_token)
        forbidden = self.client.post(
            f"/friendships/{friendship_id}/accept",
            data={"return_to": "/friends"},
        )
        self.assertEqual(forbidden.status_code, 403)

        self.login_as(self.charlie_token)
        accepted = self.client.post(
            f"/friendships/{friendship_id}/accept",
            data={"return_to": "/friends"},
            follow_redirects=False,
        )
        self.assertEqual(accepted.status_code, 303)

        with Session(engine) as session:
            friendship = session.get(Friendship, friendship_id)
            self.assertEqual(friendship.status, FriendshipStatus.ACCEPTED)
            session.delete(friendship)
            session.commit()

    def test_02_visibility_and_edit_permissions(self):
        private_id = self.create_page("Private friendship test", "private")
        friends_id = self.create_page("Friends friendship test", "friends")
        viewer_id = self.create_page(
            "Custom viewer friendship test",
            "custom",
            viewers=[self.bob_id],
        )
        editor_id = self.create_page(
            "Custom editor friendship test",
            "custom",
            editors=[self.bob_id],
        )
        public_id = self.create_page("Public friendship test", "public")

        self.login_as(self.bob_token)
        self.assertEqual(self.client.get(f"/pages/{private_id}/blocks-editor").status_code, 404)
        self.assertEqual(self.client.get(f"/pages/{friends_id}/blocks-editor").status_code, 200)

        viewer_response = self.client.get(f"/pages/{viewer_id}/blocks-editor")
        self.assertEqual(viewer_response.status_code, 200)
        self.assertIn("Somente leitura", viewer_response.text)
        self.assertEqual(
            self.client.post(f"/pages/{viewer_id}/blocks", data={"block_type": "text"}).status_code,
            403,
        )

        editor_response = self.client.get(f"/pages/{editor_id}/blocks-editor")
        self.assertEqual(editor_response.status_code, 200)
        self.assertIn("Editar página", editor_response.text)
        self.assertEqual(
            self.client.post(f"/pages/{editor_id}/blocks", data={"block_type": "text"}).status_code,
            200,
        )

        self.login_as(self.charlie_token)
        self.assertEqual(self.client.get(f"/pages/{public_id}/blocks-editor").status_code, 200)
        self.assertEqual(self.client.get(f"/pages/{friends_id}/blocks-editor").status_code, 404)

        self.login_as(self.bob_token)
        self.assertEqual(self.client.delete(f"/pages/{editor_id}").status_code, 403)

        with Session(engine) as session:
            share = session.get(PageShare, (editor_id, self.bob_id))
            self.assertIsNotNone(share)
            self.assertEqual(share.permission, PageSharePermission.EDIT)

    def test_03_removing_friendship_revokes_access(self):
        page_id = self.create_page(
            "Revoked custom friendship test",
            "custom",
            viewers=[self.bob_id],
        )

        with Session(engine) as session:
            friendship = session.exec(
                select(Friendship).where(
                    (Friendship.status == FriendshipStatus.ACCEPTED)
                    & (
                        ((Friendship.requester_id == self.alice_id) & (Friendship.addressee_id == self.bob_id))
                        | ((Friendship.requester_id == self.bob_id) & (Friendship.addressee_id == self.alice_id))
                    )
                )
            ).first()
            self.assertIsNotNone(friendship)
            friendship_id = friendship.id

        self.login_as(self.bob_token)
        removed = self.client.post(
            f"/friendships/{friendship_id}/remove",
            data={"return_to": f"/profile/{self.alice_id}"},
            follow_redirects=False,
        )
        self.assertEqual(removed.status_code, 303)
        self.assertEqual(self.client.get(f"/pages/{page_id}/blocks-editor").status_code, 404)

        with Session(engine) as session:
            self.assertIsNone(session.get(Friendship, friendship_id))
            self.assertIsNone(session.get(PageShare, (page_id, self.bob_id)))


if __name__ == "__main__":
    unittest.main()
