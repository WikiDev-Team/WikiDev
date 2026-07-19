import pytest
from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select
from starlette.requests import Request

from app.crud import create_comment
from app.models import (
    Comment,
    CommentCreate,
    Page,
    PageBlock,
    PageVisibility,
    User,
)
from app.routers.comments import (
    add_page_comment,
    add_reply,
    edit_comment,
    edit_form,
    page_discussion,
    remove_comment,
    reply_form,
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


@pytest.fixture(name="discussion")
def discussion_fixture():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        owner = User(username="owner", email="owner@example.com", display_name="Autora")
        other = User(username="other", email="other@example.com")
        session.add(owner)
        session.add(other)
        session.commit()
        session.refresh(owner)
        session.refresh(other)
        page = Page(
            title="Página discutida",
            author_id=owner.id,
            visibility=PageVisibility.PUBLIC,
        )
        session.add(page)
        session.commit()
        session.refresh(page)
        yield session, owner, other, page


def _html(response):
    return response.body.decode("utf-8")


def test_discussion_starts_collapsed_and_loads_on_toggle(discussion):
    session, owner, _, page = discussion
    response = blocks_editor(_request(), page.id, session, owner)
    html = _html(response)
    assert '<details\n        class="page-discussion"' in html
    assert 'hx-trigger="toggle once"' in html
    assert f'hx-get="/comments/pages/{page.id}"' in html
    assert "comment-form" not in html


def test_text_comment_and_htmx_partial_escape_user_html(discussion):
    session, owner, _, page = discussion
    response = add_page_comment(
        _request("POST", htmx=True),
        page.id,
        "<script>alert('texto')</script>",
        "",
        "",
        session,
        owner,
    )
    html = _html(response)
    assert f'id="page-discussion-{page.id}"' in html
    assert "&lt;script&gt;alert" in html
    assert "<script>alert" not in html
    assert "+ Adicionar código" in html
    assert "comment-code-fields" in html and "hidden" in html


@pytest.mark.parametrize("language", ["python", "java", "c", "cpp"])
def test_comment_with_each_supported_language_is_highlighted_and_escaped(
    discussion, language
):
    session, owner, _, page = discussion
    response = add_page_comment(
        _request("POST", htmx=True),
        page.id,
        f"Código {language}",
        "<img src=x onerror=alert(1)>",
        language,
        session,
        owner,
    )
    html = _html(response)
    assert f'class="language-{language}"' in html
    assert "&lt;img src=x onerror=alert(1)&gt;" in html
    assert "<img src=x" not in html


def test_code_without_language_is_rejected(discussion):
    session, owner, _, page = discussion
    with pytest.raises(HTTPException) as error:
        add_page_comment(
            _request("POST", htmx=True),
            page.id,
            "Texto",
            "print('sem linguagem')",
            "",
            session,
            owner,
        )
    assert error.value.status_code == 422


def test_reply_form_only_appears_on_request_and_replaces_shared_target(discussion):
    session, owner, _, page = discussion
    parent = create_comment(
        session,
        CommentCreate(page_id=page.id, body="Comentário"),
        author_id=owner.id,
    )
    discussion_html = _html(page_discussion(_request(), page.id, session, owner))
    assert "comment-reply-form" not in discussion_html
    assert 'hx-target="#discussion-reply-form"' in discussion_html

    form_html = _html(reply_form(_request(), parent.id, session, owner))
    assert "comment-reply-form" in form_html
    assert "Respondendo a @owner" in form_html


def test_reply_levels_one_through_four_and_rejects_fifth(discussion):
    session, owner, _, page = discussion
    parent = create_comment(
        session,
        CommentCreate(page_id=page.id, body="Raiz"),
        author_id=owner.id,
    )
    for level in range(1, 5):
        add_reply(
            _request("POST", htmx=True),
            parent.id,
            f"Resposta {level}",
            "",
            "",
            session,
            owner,
        )
        parent = session.exec(
            select(Comment).order_by(Comment.id.desc())
        ).first()

    with pytest.raises(HTTPException) as error:
        add_reply(
            _request("POST", htmx=True),
            parent.id,
            "Resposta 5",
            "",
            "",
            session,
            owner,
        )
    assert error.value.status_code == 400


def test_soft_delete_with_replies_and_page_owner_moderation(discussion):
    session, owner, other, page = discussion
    parent = create_comment(
        session,
        CommentCreate(page_id=page.id, body="Comentário de outra pessoa"),
        author_id=other.id,
    )
    create_comment(
        session,
        CommentCreate(
            page_id=page.id,
            parent_comment_id=parent.id,
            body="Resposta preservada",
        ),
        author_id=owner.id,
    )
    response = remove_comment(_request("DELETE", True), parent.id, session, owner)
    html = _html(response)
    assert "Comentário removido" in html
    assert "Resposta preservada" in html


def test_other_user_cannot_delete_comment(discussion):
    session, owner, other, page = discussion
    comment = create_comment(
        session,
        CommentCreate(page_id=page.id, body="Da autora"),
        author_id=owner.id,
    )
    with pytest.raises(HTTPException) as error:
        remove_comment(_request("DELETE", True), comment.id, session, other)
    assert error.value.status_code == 403
    assert comment.is_deleted is False


def test_block_comments_are_not_rendered_in_page_discussion(discussion):
    session, owner, _, page = discussion
    block = PageBlock(page_id=page.id, content="Bloco")
    session.add(block)
    session.commit()
    session.refresh(block)
    create_comment(
        session,
        CommentCreate(page_id=page.id, block_id=block.id, body="Somente no bloco"),
        author_id=owner.id,
    )
    html = _html(page_discussion(_request(), page.id, session, owner))
    assert "Somente no bloco" not in html


def test_author_can_open_prefilled_edit_form_and_update_comment(discussion):
    session, owner, _, page = discussion
    comment = create_comment(
        session,
        CommentCreate(
            page_id=page.id,
            body="Texto original",
            code="print('original')",
            language="python",
        ),
        author_id=owner.id,
    )
    form_html = _html(edit_form(_request(), comment.id, session, owner))
    assert 'hx-patch="/comments/' in form_html
    assert "Texto original" in form_html
    assert "print(&#39;original&#39;)" in form_html
    assert 'value="python" selected' in form_html

    response = edit_comment(
        _request("PATCH", True),
        comment.id,
        "Texto alterado",
        "System.out.println(\"ok\");",
        "java",
        session,
        owner,
    )
    html = _html(response)
    assert "Texto alterado" in html
    assert 'class="language-java"' in html
    assert "Texto original" not in html


def test_edit_escapes_html_and_validates_code_language(discussion):
    session, owner, _, page = discussion
    comment = create_comment(
        session,
        CommentCreate(page_id=page.id, body="Original"),
        author_id=owner.id,
    )
    response = edit_comment(
        _request("PATCH", True),
        comment.id,
        "<strong>não renderizar</strong>",
        "<script>alert(1)</script>",
        "cpp",
        session,
        owner,
    )
    html = _html(response)
    assert "&lt;strong&gt;não renderizar&lt;/strong&gt;" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<strong>não renderizar</strong>" not in html

    with pytest.raises(HTTPException) as error:
        edit_comment(
            _request("PATCH", True),
            comment.id,
            "Continua válido",
            "int main() {}",
            "",
            session,
            owner,
        )
    assert error.value.status_code == 422


def test_only_comment_author_can_edit_even_when_user_owns_page(discussion):
    session, owner, other, page = discussion
    other_comment = create_comment(
        session,
        CommentCreate(page_id=page.id, body="Texto de outra pessoa"),
        author_id=other.id,
    )
    with pytest.raises(HTTPException) as get_error:
        edit_form(_request(), other_comment.id, session, owner)
    assert get_error.value.status_code == 403
    with pytest.raises(HTTPException) as patch_error:
        edit_comment(
            _request("PATCH", True),
            other_comment.id,
            "Tentativa",
            "",
            "",
            session,
            owner,
        )
    assert patch_error.value.status_code == 403


def test_removed_comment_cannot_be_edited(discussion):
    session, owner, _, page = discussion
    comment = create_comment(
        session,
        CommentCreate(page_id=page.id, body="Será removido"),
        author_id=owner.id,
    )
    remove_comment(_request("DELETE", True), comment.id, session, owner)
    with pytest.raises(HTTPException) as get_error:
        edit_form(_request(), comment.id, session, owner)
    assert get_error.value.status_code == 400
    with pytest.raises(HTTPException) as patch_error:
        edit_comment(
            _request("PATCH", True),
            comment.id,
            "Não pode",
            "",
            "",
            session,
            owner,
        )
    assert patch_error.value.status_code == 422
