from dataclasses import dataclass, field

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..crud import (
    COMMENT_LANGUAGES,
    MAX_COMMENT_REPLY_LEVELS,
    create_comment,
    delete_comment,
    get_comment_depth,
    update_comment,
)
from ..db import get_session
from ..dependencies import get_current_user
from ..models import Comment, CommentCreate, CommentUpdate, Page, User
from ..permissions import require_page_view
from ..templates import templates

router = APIRouter(prefix="/comments", tags=["comments"])
_LANGUAGE_LABELS = {
    "python": "Python",
    "java": "Java",
    "c": "C",
    "cpp": "C++",
}
COMMENT_LANGUAGE_LABELS = {
    language: label
    for language, label in _LANGUAGE_LABELS.items()
    if language in COMMENT_LANGUAGES
}


@dataclass
class CommentNode:
    comment: Comment
    depth: int = 0
    replying_to: User | None = None
    replies: list["CommentNode"] = field(default_factory=list)


def _page_or_404(session: Session, page_id: int) -> Page:
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return page


def _comment_or_404(session: Session, comment_id: int) -> Comment:
    comment = session.get(Comment, comment_id)
    if comment is None or comment.block_id is not None:
        raise HTTPException(status_code=404, detail="Comentário não encontrado")
    return comment


def _page_comment_tree(session: Session, page_id: int) -> list[CommentNode]:
    comments = session.exec(
        select(Comment)
        .where(Comment.page_id == page_id, Comment.block_id.is_(None))
        .order_by(Comment.created_at.asc(), Comment.id.asc())
    ).all()
    nodes = {comment.id: CommentNode(comment=comment) for comment in comments}
    roots: list[CommentNode] = []
    for comment in comments:
        node = nodes[comment.id]
        parent = nodes.get(comment.parent_comment_id)
        if parent is None:
            roots.append(node)
        else:
            node.depth = parent.depth + 1
            node.replying_to = parent.comment.author
            parent.replies.append(node)

    def visible(node: CommentNode) -> bool:
        node.replies = [reply for reply in node.replies if visible(reply)]
        return not node.comment.is_deleted or bool(node.replies)

    return [root for root in roots if visible(root)]


def _render_discussion(
    request: Request,
    session: Session,
    page: Page,
    current_user: User,
):
    return templates.TemplateResponse(
        request=request,
        name="partials/page_discussion.html",
        context={
            "page": page,
            "comment_nodes": _page_comment_tree(session, page.id),
            "current_user": current_user,
            "comment_languages": COMMENT_LANGUAGE_LABELS,
            "max_reply_levels": MAX_COMMENT_REPLY_LEVELS,
        },
    )


def _create_payload(body: str, code: str, language: str, **ids) -> CommentCreate:
    return CommentCreate(
        body=body,
        code=code or None,
        language=language or None,
        **ids,
    )


@router.get("/pages/{page_id}", response_class=HTMLResponse)
def page_discussion(
    request: Request,
    page_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page_or_404(session, page_id)
    require_page_view(session, page, current_user)
    return _render_discussion(request, session, page, current_user)


@router.post("/pages/{page_id}", response_class=HTMLResponse, status_code=201)
def add_page_comment(
    request: Request,
    page_id: int,
    body: str = Form(...),
    code: str = Form(""),
    language: str = Form(""),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page_or_404(session, page_id)
    require_page_view(session, page, current_user)
    try:
        create_comment(
            session,
            _create_payload(
                page_id=page.id, body=body, code=code, language=language
            ),
            author_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _render_discussion(request, session, page, current_user)


@router.get("/{comment_id}/reply", response_class=HTMLResponse)
def reply_form(
    request: Request,
    comment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    comment = _comment_or_404(session, comment_id)
    page = _page_or_404(session, comment.page_id)
    require_page_view(session, page, current_user)
    if comment.is_deleted:
        raise HTTPException(status_code=400, detail="Comentário removido")
    if get_comment_depth(session, comment) >= MAX_COMMENT_REPLY_LEVELS:
        raise HTTPException(status_code=400, detail="Limite de respostas atingido")
    return templates.TemplateResponse(
        request=request,
        name="partials/comment_form.html",
        context={
            "page": page,
            "parent": comment,
            "comment_languages": COMMENT_LANGUAGE_LABELS,
        },
    )


@router.post("/{comment_id}/replies", response_class=HTMLResponse, status_code=201)
def add_reply(
    request: Request,
    comment_id: int,
    body: str = Form(...),
    code: str = Form(""),
    language: str = Form(""),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    parent = _comment_or_404(session, comment_id)
    page = _page_or_404(session, parent.page_id)
    require_page_view(session, page, current_user)
    try:
        create_comment(
            session,
            _create_payload(
                page_id=page.id,
                parent_comment_id=parent.id,
                body=body,
                code=code,
                language=language,
            ),
            author_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _render_discussion(request, session, page, current_user)


@router.get("/{comment_id}/edit", response_class=HTMLResponse)
def edit_form(
    request: Request,
    comment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    comment = _comment_or_404(session, comment_id)
    page = _page_or_404(session, comment.page_id)
    require_page_view(session, page, current_user)
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não pode editar este comentário")
    if comment.is_deleted:
        raise HTTPException(status_code=400, detail="Comentário removido")
    return templates.TemplateResponse(
        request=request,
        name="partials/comment_form.html",
        context={
            "page": page,
            "editing_comment": comment,
            "comment_languages": COMMENT_LANGUAGE_LABELS,
        },
    )


@router.patch("/{comment_id}", response_class=HTMLResponse)
def edit_comment(
    request: Request,
    comment_id: int,
    body: str = Form(...),
    code: str = Form(""),
    language: str = Form(""),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    comment = _comment_or_404(session, comment_id)
    page = _page_or_404(session, comment.page_id)
    require_page_view(session, page, current_user)
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não pode editar este comentário")
    try:
        update_comment(
            session,
            comment,
            CommentUpdate(
                body=body,
                code=code or None,
                language=language or None,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _render_discussion(request, session, page, current_user)


@router.delete("/{comment_id}", response_class=HTMLResponse)
def remove_comment(
    request: Request,
    comment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    comment = _comment_or_404(session, comment_id)
    page = _page_or_404(session, comment.page_id)
    require_page_view(session, page, current_user)
    if comment.author_id != current_user.id and page.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não pode remover este comentário")
    delete_comment(session, comment)
    return _render_discussion(request, session, page, current_user)
