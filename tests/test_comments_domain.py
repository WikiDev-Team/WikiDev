import pytest
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.crud import (
    create_comment,
    delete_comment,
    get_comment_depth,
    update_comment,
)
from app.models import CommentCreate, CommentUpdate, Page, PageBlock, User


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
        page = Page(title="Página", author_id=user.id)
        other_page = Page(title="Outra página", author_id=user.id)
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


def test_schemas_do_not_accept_server_owned_fields():
    with pytest.raises(ValidationError):
        CommentCreate(page_id=1, body="texto", author_id=99)
    with pytest.raises(ValidationError):
        CommentUpdate(body="texto", is_deleted=True)


def test_general_block_and_reply_comments(domain):
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

    assert general.body == "geral" and general.block_id is None
    assert block_comment.code == "print('ok')"
    assert block_comment.language == "python"
    assert reply.parent_comment_id == block_comment.id
    assert get_comment_depth(session, reply) == 1


@pytest.mark.parametrize("body", ["", "   ", "\n\t"])
def test_text_is_required_after_strip(domain, body):
    session, user, page, *_ = domain
    with pytest.raises(ValueError, match="texto"):
        create_comment(
            session, CommentCreate(page_id=page.id, body=body), author_id=user.id
        )


def test_code_language_rules(domain):
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
                page_id=page.id, body="texto", code="puts 1", language="ruby"
            ),
            author_id=user.id,
        )
    comment = create_comment(
        session,
        CommentCreate(page_id=page.id, body="texto", language="java"),
        author_id=user.id,
    )
    assert comment.code is None and comment.language is None


def test_block_and_parent_must_match_page_and_discussion(domain):
    session, user, page, other_page, block, other_block = domain
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
            CommentCreate(
                page_id=page.id, parent_comment_id=parent.id, body="resposta"
            ),
            author_id=user.id,
        )


def test_allows_four_reply_levels_and_rejects_fifth(domain):
    session, user, page, *_ = domain
    parent = create_comment(
        session, CommentCreate(page_id=page.id, body="raiz"), author_id=user.id
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
                page_id=page.id, parent_comment_id=parent.id, body="nível 5"
            ),
            author_id=user.id,
        )


def test_cycle_detection(domain):
    session, user, page, *_ = domain
    root = create_comment(
        session, CommentCreate(page_id=page.id, body="raiz"), author_id=user.id
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


def test_soft_delete_preserves_record_and_blocks_edit_or_reply(domain):
    session, user, page, *_ = domain
    comment = create_comment(
        session, CommentCreate(page_id=page.id, body="texto"), author_id=user.id
    )
    comment_id = comment.id
    delete_comment(session, comment)

    assert session.get(type(comment), comment_id).is_deleted is True
    with pytest.raises(ValueError, match="não pode ser editado"):
        update_comment(session, comment, CommentUpdate(body="alterado"))
    with pytest.raises(ValueError, match="comentário excluído"):
        create_comment(
            session,
            CommentCreate(
                page_id=page.id, parent_comment_id=comment.id, body="resposta"
            ),
            author_id=user.id,
        )
