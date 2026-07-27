from __future__ import annotations

from datetime import timedelta

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.crud import create_comment, delete_comment
from app.models import CommentCreate, Page, PageBlock, PageVisibility, User
from app.routers.forum import list_recent_discussions


def _comment(session: Session, user: User, page: Page, body: str, block: PageBlock | None = None):
    return create_comment(
        session,
        CommentCreate(page_id=page.id, block_id=block.id if block else None, body=body),
        author_id=user.id,
    )


def test_forum_groups_page_and_block_discussions_by_latest_activity():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(username="ada", email="ada@example.com")
        page = Page(title="Página", slug="pagina", author_id=1, visibility=PageVisibility.PUBLIC)
        session.add(user)
        session.commit()
        page.author_id = user.id
        session.add(page)
        session.commit()
        session.refresh(page)
        block = PageBlock(page_id=page.id, content="print('ok')")
        session.add(block)
        session.commit()
        session.refresh(block)

        general = _comment(session, user, page, "Geral")
        block_comment = _comment(session, user, page, "No bloco", block)
        general.created_at = general.created_at - timedelta(minutes=1)
        session.add(general)
        session.commit()

        discussions = list_recent_discussions(session, user)
        assert len(discussions) == 2
        assert discussions[0].block.id == block.id
        assert discussions[0].comment_count == 1
        assert discussions[1].block is None


def test_forum_ignores_deleted_comments_and_private_pages():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        owner = User(username="owner", email="owner@example.com")
        reader = User(username="reader", email="reader@example.com")
        session.add(owner)
        session.add(reader)
        session.commit()
        public_page = Page(title="Pública", slug="publica", author_id=owner.id, visibility=PageVisibility.PUBLIC)
        private_page = Page(title="Privada", slug="privada", author_id=owner.id)
        session.add(public_page)
        session.add(private_page)
        session.commit()
        session.refresh(public_page)
        session.refresh(private_page)

        deleted = _comment(session, owner, public_page, "Removido")
        delete_comment(session, deleted)
        _comment(session, owner, public_page, "Visível")
        _comment(session, owner, private_page, "Segredo")

        discussions = list_recent_discussions(session, reader)
        assert len(discussions) == 1
        assert discussions[0].page.id == public_page.id
        assert discussions[0].comment_count == 1


def test_forum_returns_empty_list_when_no_accessible_activity():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(username="ada", email="ada@example.com")
        session.add(user)
        session.commit()
        assert list_recent_discussions(session, user) == []
