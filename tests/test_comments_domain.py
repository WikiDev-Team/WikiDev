from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.crud import (
    create_comment,
    delete_comment,
    delete_page,
    delete_page_block,
    get_comment_depth,
    update_comment,
)
from app.models import Comment, CommentCreate, CommentUpdate, Page, PageBlock, User


@pytest.fixture(name="domain")
def domain_fixture():
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

        page = Page(title="Página", slug="pagina", author_id=user.id)
        other_page = Page(
            title="Outra página",
            slug="outra-pagina",
            author_id=user.id,
        )
        session.add(page)
        session.add(other_page)
        session.commit()
        session.refresh(page)
        session.refresh(other_page)

        block = PageBlock(page_id=page.id, content="Bloco")
        other_block = PageBlock(page_id=other_page.id, content="Outro bloco")
        session.add(block)
        session.add(other_block)
        session.commit()
        session.refresh(block)
        session.refresh(other_block)

        yield session, user, page, other_page, block, other_block


def test_schemas_reject_server_owned_fields():
    with pytest.raises(ValidationError):
        CommentCreate(page_id=1, body="texto", author_id=99)
    with pytest.raises(ValidationError):
        CommentUpdate(body="texto", is_deleted=True)


def test_creates_general_block_and_reply_comments(domain):
    session, user, page, _, block, _ = domain
    general = create_comment(
        session,
        CommentCreate(page_id=page.id, body="  geral  "),
        author_id=user.id,
    )
    block_comment = create_comment(
        session,
        CommentCreate(
            page_id=page.id,
            block_id=block.id,
            body="com código",
            code=" print('ok') ",
            language="Python",
        ),
        author_id=user.id,
    )
    reply = create_comment(
        session,
        CommentCreate(
            page_id=page.id,
            block_id=block.id,
            parent_comment_id=block_comment.id,
            body="resposta",
        ),
        author_id=user.id,
    )

    assert general.body == "geral"
    assert general.block_id is None
    assert block_comment.code == "print('ok')"
    assert block_comment.language == "python"
    assert reply.parent_comment_id == block_comment.id
    assert get_comment_depth(session, reply) == 1


@pytest.mark.parametrize("body", ["", "   ", "\n\t"])
def test_rejects_empty_comment_after_normalization(domain, body):
    session, user, page, *_ = domain

    with pytest.raises(ValueError, match="vazio"):
        create_comment(
            session,
            CommentCreate(page_id=page.id, body=body),
            author_id=user.id,
        )


def test_validates_code_language(domain):
    session, user, page, *_ = domain

    with pytest.raises(ValueError, match="linguagem"):
        create_comment(
            session,
            CommentCreate(page_id=page.id, body="texto", code="x = 1"),
            author_id=user.id,
        )
    with pytest.raises(ValueError, match="linguagem"):
        create_comment(
            session,
            CommentCreate(
                page_id=page.id,
                body="texto",
                code="puts 1",
                language="ruby",
            ),
            author_id=user.id,
        )

    comment = create_comment(
        session,
        CommentCreate(page_id=page.id, body="texto", language="java"),
        author_id=user.id,
    )
    assert comment.code is None
    assert comment.language is None


def test_requires_block_and_parent_to_share_the_same_discussion(domain):
    session, user, page, other_page, block, other_block = domain

    with pytest.raises(ValueError, match="Bloco não encontrado"):
        create_comment(
            session,
            CommentCreate(page_id=page.id, block_id=999, body="texto"),
            author_id=user.id,
        )
    with pytest.raises(ValueError, match="não pertence"):
        create_comment(
            session,
            CommentCreate(page_id=page.id, block_id=other_block.id, body="texto"),
            author_id=user.id,
        )

    parent = create_comment(
        session,
        CommentCreate(page_id=page.id, block_id=block.id, body="pai"),
        author_id=user.id,
    )
    with pytest.raises(ValueError, match="mesma página"):
        create_comment(
            session,
            CommentCreate(
                page_id=other_page.id,
                block_id=other_block.id,
                parent_comment_id=parent.id,
                body="resposta",
            ),
            author_id=user.id,
        )
    with pytest.raises(ValueError, match="mesma discussão"):
        create_comment(
            session,
            CommentCreate(page_id=page.id, parent_comment_id=parent.id, body="resposta"),
            author_id=user.id,
        )


def test_allows_four_reply_levels_and_rejects_the_fifth(domain):
    session, user, page, *_ = domain
    parent = create_comment(
        session,
        CommentCreate(page_id=page.id, body="raiz"),
        author_id=user.id,
    )

    for level in range(1, 5):
        parent = create_comment(
            session,
            CommentCreate(
                page_id=page.id,
                parent_comment_id=parent.id,
                body=f"nível {level}",
            ),
            author_id=user.id,
        )
        assert get_comment_depth(session, parent) == level

    with pytest.raises(ValueError, match="quatro níveis"):
        create_comment(
            session,
            CommentCreate(
                page_id=page.id,
                parent_comment_id=parent.id,
                body="nível 5",
            ),
            author_id=user.id,
        )


def test_detects_circular_comment_references(domain):
    session, user, page, *_ = domain
    root = create_comment(
        session,
        CommentCreate(page_id=page.id, body="raiz"),
        author_id=user.id,
    )
    child = create_comment(
        session,
        CommentCreate(page_id=page.id, parent_comment_id=root.id, body="filho"),
        author_id=user.id,
    )

    root.parent_comment_id = child.id
    session.add(root)
    session.commit()

    with pytest.raises(ValueError, match="circular"):
        get_comment_depth(session, child)


def test_soft_delete_preserves_comment_and_blocks_edits_and_replies(domain):
    session, user, page, *_ = domain
    comment = create_comment(
        session,
        CommentCreate(page_id=page.id, body="texto"),
        author_id=user.id,
    )
    comment_id = comment.id
    delete_comment(session, comment)

    deleted = session.get(Comment, comment_id)
    assert deleted is not None
    assert deleted.is_deleted is True
    assert deleted.body == "[comentário removido]"
    with pytest.raises(ValueError, match="não pode ser editado"):
        update_comment(session, deleted, CommentUpdate(body="alterado"))
    with pytest.raises(ValueError, match="comentário removido"):
        create_comment(
            session,
            CommentCreate(
                page_id=page.id,
                parent_comment_id=deleted.id,
                body="resposta",
            ),
            author_id=user.id,
        )


def test_deleting_block_and_page_removes_their_comments(domain):
    session, user, page, _, block, _ = domain
    block_comment = create_comment(
        session,
        CommentCreate(page_id=page.id, block_id=block.id, body="no bloco"),
        author_id=user.id,
    )
    page_comment = create_comment(
        session,
        CommentCreate(page_id=page.id, body="na página"),
        author_id=user.id,
    )
    block_comment_id = block_comment.id
    page_comment_id = page_comment.id

    delete_page_block(session, block)
    assert session.get(Comment, block_comment_id) is None
    assert session.get(Comment, page_comment_id) is not None

    delete_page(session, page)
    assert session.get(Comment, page_comment_id) is None
