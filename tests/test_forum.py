import asyncio
from datetime import datetime

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine
from starlette.requests import Request

from app.crud import create_comment, delete_comment
from app.main import dashboard
from app.models import (
    CommentCreate,
    Page,
    PageBlock,
    PageVisibility,
    User,
)
from app.routers.forum import forum, list_recent_discussions


def _request():
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/forum",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "scheme": "http",
        }
    )


def _set_created_at(session, comment, value):
    comment.created_at = value
    session.add(comment)
    session.commit()
    session.refresh(comment)


def _setup():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    viewer = User(username="viewer", email="viewer@example.com")
    second_author = User(username="second", email="second@example.com")
    hidden_owner = User(username="hidden", email="hidden@example.com")
    session.add_all([viewer, second_author, hidden_owner])
    session.commit()
    for user in (viewer, second_author, hidden_owner):
        session.refresh(user)
    public_page = Page(
        title="Página pública",
        summary="Resumo visível",
        author_id=viewer.id,
        visibility=PageVisibility.PUBLIC,
    )
    empty_page = Page(
        title="Sem comentários",
        author_id=viewer.id,
        visibility=PageVisibility.PUBLIC,
    )
    private_page = Page(
        title="Segredo que não pode vazar",
        author_id=hidden_owner.id,
        visibility=PageVisibility.PRIVATE,
    )
    session.add_all([public_page, empty_page, private_page])
    session.commit()
    for page in (public_page, empty_page, private_page):
        session.refresh(page)
    block = PageBlock(page_id=public_page.id, content="Trecho identificável do bloco")
    private_block = PageBlock(page_id=private_page.id, content="Bloco secreto")
    session.add_all([block, private_block])
    session.commit()
    session.refresh(block)
    session.refresh(private_block)
    return (
        session,
        viewer,
        second_author,
        hidden_owner,
        public_page,
        empty_page,
        private_page,
        block,
        private_block,
    )


def test_recent_forum_groups_page_and_block_and_orders_by_latest_reply():
    (
        session,
        viewer,
        second_author,
        _,
        page,
        empty_page,
        _,
        block,
        _,
    ) = _setup()
    try:
        general = create_comment(
            session,
            CommentCreate(page_id=page.id, body="Discussão geral"),
            author_id=viewer.id,
        )
        _set_created_at(session, general, datetime(2026, 1, 1, 10, 0))
        block_comment = create_comment(
            session,
            CommentCreate(page_id=page.id, block_id=block.id, body="No bloco"),
            author_id=viewer.id,
        )
        _set_created_at(session, block_comment, datetime(2026, 1, 2, 10, 0))

        entries = list_recent_discussions(session, viewer)
        assert len(entries) == 2
        assert entries[0].block.id == block.id
        assert entries[1].block is None
        assert all(entry.page.id != empty_page.id for entry in entries)

        reply = create_comment(
            session,
            CommentCreate(
                page_id=page.id,
                parent_comment_id=general.id,
                body="Resposta nova",
            ),
            author_id=second_author.id,
        )
        _set_created_at(session, reply, datetime(2026, 1, 3, 10, 0))
        entries = list_recent_discussions(session, viewer)
        assert entries[0].block is None
        assert entries[0].comment_count == 2
        assert entries[0].latest_activity == datetime(2026, 1, 3, 10, 0)
        assert entries[0].latest_author.id == second_author.id
    finally:
        session.close()


def test_deleted_comment_does_not_count_or_define_latest_activity():
    session, viewer, _, _, page, _, _, _, _ = _setup()
    try:
        active = create_comment(
            session,
            CommentCreate(page_id=page.id, body="Ativo"),
            author_id=viewer.id,
        )
        _set_created_at(session, active, datetime(2026, 2, 1, 9, 0))
        removed = create_comment(
            session,
            CommentCreate(page_id=page.id, body="Removido mais novo"),
            author_id=viewer.id,
        )
        _set_created_at(session, removed, datetime(2026, 2, 2, 9, 0))
        delete_comment(session, removed)

        entry = list_recent_discussions(session, viewer)[0]
        assert entry.comment_count == 1
        assert entry.latest_activity == active.created_at
    finally:
        session.close()


def test_private_page_and_block_do_not_leak_in_forum():
    session, viewer, _, hidden_owner, _, _, private_page, _, private_block = _setup()
    try:
        create_comment(
            session,
            CommentCreate(page_id=private_page.id, body="Segredo geral"),
            author_id=hidden_owner.id,
        )
        create_comment(
            session,
            CommentCreate(
                page_id=private_page.id,
                block_id=private_block.id,
                body="Segredo no bloco",
            ),
            author_id=hidden_owner.id,
        )
        response = forum(_request(), session, viewer)
        html = response.body.decode()
        assert "Segredo que não pode vazar" not in html
        assert "Bloco secreto" not in html
        assert list_recent_discussions(session, viewer) == []
    finally:
        session.close()


def test_forum_links_open_page_or_block_discussion():
    session, viewer, _, _, page, _, _, block, _ = _setup()
    try:
        create_comment(
            session,
            CommentCreate(page_id=page.id, body="Geral"),
            author_id=viewer.id,
        )
        create_comment(
            session,
            CommentCreate(page_id=page.id, block_id=block.id, body="Bloco"),
            author_id=viewer.id,
        )
        entries = list_recent_discussions(session, viewer)
        urls = {entry.block.id if entry.block else None: entry.url for entry in entries}
        assert urls[None] == f"/dashboard?open_page={page.id}&discussion=page"
        assert urls[block.id] == (
            f"/dashboard?open_page={page.id}&discussion=block-{block.id}"
        )

        page_html = asyncio.run(
            dashboard(_request(), page.id, "page", session, viewer)
        ).body.decode()
        block_html = asyncio.run(
            dashboard(_request(), page.id, f"block-{block.id}", session, viewer)
        ).body.decode()
        assert f'page-discussion-panel-{page.id}' in page_html
        assert f'block-discussion-panel-{block.id}' in block_html
    finally:
        session.close()


def test_empty_forum_state():
    session, viewer, *_ = _setup()
    try:
        response = forum(_request(), session, viewer)
        html = response.body.decode()
        assert "Ainda não há discussões acessíveis." in html
        assert "forum-discussion-row" not in html
    finally:
        session.close()
