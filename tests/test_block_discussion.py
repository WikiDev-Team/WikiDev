import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select
from starlette.requests import Request

from app.crud import create_comment, delete_comment
from app.models import (
    Comment,
    CommentCreate,
    Page,
    PageBlock,
    PageBlockType,
    PageVisibility,
    User,
)
from app.routers.comments import (
    add_block_comment,
    add_page_comment,
    add_reply,
    block_discussion,
    page_discussion,
)
from app.routers.page_blocks import blocks_editor


def _request(method="GET", htmx=False):
    headers = [(b"hx-request", b"true")] if htmx else []
    return Request(
        {
            "type": "http",
            "method": method,
            "path": "/",
            "headers": headers,
            "query_string": b"",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "scheme": "http",
        }
    )


def _html(response):
    return response.body.decode("utf-8")


@pytest.fixture(name="blocks_env")
def blocks_env_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(username="author", email="author@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)
        page = Page(
            title="Página com blocos",
            author_id=user.id,
            visibility=PageVisibility.PUBLIC,
        )
        session.add(page)
        session.commit()
        session.refresh(page)
        text_block = PageBlock(
            page_id=page.id,
            block_type=PageBlockType.TEXT,
            content="Texto",
        )
        code_block = PageBlock(
            page_id=page.id,
            block_type=PageBlockType.CODE,
            content="print('página')",
            language="python",
        )
        session.add(text_block)
        session.add(code_block)
        session.commit()
        session.refresh(text_block)
        session.refresh(code_block)
        yield session, user, page, text_block, code_block


def test_each_block_has_lazy_discrete_control_and_stable_anchor(blocks_env):
    session, user, page, text_block, code_block = blocks_env
    html = _html(blocks_editor(_request(), page.id, session, user))
    for block in (text_block, code_block):
        assert f'id="block-{block.id}"' in html
        assert f'id="block-discussion-panel-{block.id}"' in html
        assert f'hx-get="/comments/blocks/{block.id}"' in html
        assert f'id="block-discussion-{block.id}"' in html
    assert html.count('hx-trigger="toggle once"') == 3  # dois blocos e discussão geral
    assert html.count('name="block-discussions"') == 2
    assert "comment-form" not in html


def test_general_and_block_discussions_are_isolated(blocks_env):
    session, user, page, text_block, code_block = blocks_env
    add_page_comment(
        _request("POST", True), page.id, "Somente geral", "", "", session, user
    )
    add_block_comment(
        _request("POST", True),
        text_block.id,
        "Somente texto",
        "",
        "",
        session,
        user,
    )
    add_block_comment(
        _request("POST", True),
        code_block.id,
        "Somente código",
        "",
        "",
        session,
        user,
    )

    general_html = _html(page_discussion(_request(), page.id, session, user))
    text_html = _html(block_discussion(_request(), text_block.id, session, user))
    code_html = _html(block_discussion(_request(), code_block.id, session, user))
    assert "Somente geral" in general_html
    assert "Somente texto" not in general_html and "Somente código" not in general_html
    assert "Somente texto" in text_html and "Somente código" not in text_html
    assert "Somente código" in code_html and "Somente texto" not in code_html
    assert "Somente geral" not in text_html and "Somente geral" not in code_html


@pytest.mark.parametrize("block_index", [0, 1])
def test_comments_work_for_text_and_code_blocks(blocks_env, block_index):
    session, user, _, text_block, code_block = blocks_env
    block = (text_block, code_block)[block_index]
    response = add_block_comment(
        _request("POST", True),
        block.id,
        "Comentário com exemplo",
        "int main() {}",
        "cpp",
        session,
        user,
    )
    html = _html(response)
    assert f'id="block-discussion-{block.id}"' in html
    assert 'class="language-cpp"' in html
    assert 'hx-swap-oob="innerHTML"' in html
    assert "💬 1" in html


def test_block_reply_keeps_scope_and_uses_unique_inline_form(blocks_env):
    session, user, page, text_block, _ = blocks_env
    parent = create_comment(
        session,
        CommentCreate(page_id=page.id, block_id=text_block.id, body="Pai"),
        author_id=user.id,
    )
    response = add_reply(
        _request("POST", True),
        parent.id,
        "Resposta",
        "",
        "",
        session,
        user,
    )
    reply = session.exec(select(Comment).order_by(Comment.id.desc())).first()
    assert reply.parent_comment_id == parent.id
    assert reply.block_id == text_block.id
    html = _html(response)
    assert f'id="block-discussion-{text_block.id}-inline-form"' in html
    assert f'hx-target="#block-discussion-{text_block.id}-inline-form"' in html


def test_missing_block_returns_404(blocks_env):
    session, user, *_ = blocks_env
    with pytest.raises(HTTPException) as error:
        block_discussion(_request(), 999_999, session, user)
    assert error.value.status_code == 404
    with pytest.raises(HTTPException) as create_error:
        add_block_comment(
            _request("POST", True),
            999_999,
            "Texto",
            "",
            "",
            session,
            user,
        )
    assert create_error.value.status_code == 404


def test_active_count_includes_replies_and_excludes_deleted(blocks_env):
    session, user, page, text_block, _ = blocks_env
    root = create_comment(
        session,
        CommentCreate(page_id=page.id, block_id=text_block.id, body="Raiz"),
        author_id=user.id,
    )
    create_comment(
        session,
        CommentCreate(
            page_id=page.id,
            block_id=text_block.id,
            parent_comment_id=root.id,
            body="Resposta ativa",
        ),
        author_id=user.id,
    )
    deleted = create_comment(
        session,
        CommentCreate(page_id=page.id, block_id=text_block.id, body="Removido"),
        author_id=user.id,
    )
    delete_comment(session, deleted)

    html = _html(blocks_editor(_request(), page.id, session, user))
    assert f'id="block-comment-summary-{text_block.id}"' in html
    assert "💬 2" in html
    assert "💬 3" not in html
