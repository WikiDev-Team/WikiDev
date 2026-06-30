import os
import tempfile
import unittest

from fastapi.testclient import TestClient
from sqlmodel import Session, select


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(cls.temp_dir.name, "wikidev_test.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

        from app.db import engine, init_db
        from app.crud import create_user
        from app.main import app
        from app.models import Page, UserCreate

        init_db()
        cls.app = app
        cls.client = TestClient(app)

        with Session(engine) as session:
            user = create_user(
                session,
                UserCreate(
                    username="searcher",
                    email="searcher@example.com",
                    display_name="Searcher",
                    password="secret123",
                ),
            )
            user.token = "test-token"
            session.add(user)
            session.commit()
            session.refresh(user)
            cls.user = user

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_search_returns_pages_created_by_current_user(self):
        self.client.cookies.set("session_token", self.user.token)

        response = self.client.post(
            "/pages/",
            data={
                "title": "Busca de páginas",
                "summary": "Página usada para testar a busca",
                "content": "Conteúdo",
                "page_type": "personal",
                "status": "draft",
                "tag_ids": "",
            },
            headers={"HX-Request": "true"},
        )

        self.assertEqual(response.status_code, 200)

        from app.db import engine
        from app.models import Page

        with Session(engine) as session:
            page = session.exec(select(Page).where(Page.title == "Busca de páginas")).first()
            self.assertIsNotNone(page)
            self.assertEqual(page.author_id, self.user.id)

        search_response = self.client.get("/busca", params={"q": "busca"})
        self.assertEqual(search_response.status_code, 200)
        self.assertIn("Busca de páginas", search_response.text)


if __name__ == "__main__":
    unittest.main()
