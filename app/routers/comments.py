from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..crud import MAX_COMMENT_REPLY_LEVELS, create_comment, delete_comment, update_comment
from ..db import get_session
from ..dependencies import get_current_user
from ..models import Comment, CommentCreate, CommentRead, CommentUpdate, Page, PageBlock, User
from ..permissions import can_view_page, require_page_view
from ..templates import templates

router = APIRouter(prefix="/comments", tags=["comments"])
COMMENT_LANGUAGE_LABELS = {
    "python": "Python",
    "c": "C",
    "cpp": "C++",
    "java": "Java",
}


@dataclass
class CommentNode:
    comment: Comment
    depth: int = 0
    replying_to: User | None = None
    replies: list["CommentNode"] = field(default_factory=list)


def _comment_or_404(session: Session, comment_id: int) -> Comment:
    comment = session.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comentário não encontrado")
    return comment


def _page_or_404(session: Session, page_id: int) -> Page:
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return page


def _block_or_404(session: Session, block_id: int) -> PageBlock:
    block = session.get(PageBlock, block_id)
    if block is None:
        raise HTTPException(status_code=404, detail="Bloco não encontrado")
    return block


def _require_comment_author(comment: Comment, current_user: User) -> None:
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não pode alterar este comentário")


def _comment_tree(session: Session, page_id: int, block_id: int | None = None) -> list[CommentNode]:
    scope = Comment.block_id.is_(None) if block_id is None else Comment.block_id == block_id
    comments = session.exec(
        select(Comment)
        .where(Comment.page_id == page_id, scope)
        .order_by(Comment.created_at, Comment.id)
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
    block: PageBlock | None = None,
):
    return templates.TemplateResponse(
        request=request,
        name="partials/page_discussion.html",
        context={
            "page": page,
            "current_user": current_user,
            "comment_nodes": _comment_tree(session, page.id, block.id if block else None),
            "comment_languages": COMMENT_LANGUAGE_LABELS,
            "max_reply_levels": MAX_COMMENT_REPLY_LEVELS,
            "discussion_id": f"block-discussion-{block.id}" if block else f"page-discussion-{page.id}",
            "block": block,
            "active_comment_count": (
                len(session.exec(select(Comment).where(Comment.block_id == block.id, Comment.is_deleted.is_(False))).all())
                if block
                else None
            ),
        },
    )


def _render_page_discussion(request: Request, session: Session, page: Page, current_user: User):
    return _render_discussion(request, session, page, current_user)


@router.get("/", response_model=list[CommentRead])
def list_comments(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    page_id: int | None = None,
):
    statement = select(Comment).order_by(Comment.created_at)
    if page_id is not None:
        page = _page_or_404(session, page_id)
        require_page_view(session, page, current_user)
        return session.exec(statement.where(Comment.page_id == page_id)).all()

    comments = session.exec(statement).all()
    page_cache: dict[int, Page | None] = {}
    visible: list[Comment] = []
    for comment in comments:
        if comment.page_id not in page_cache:
            page_cache[comment.page_id] = session.get(Page, comment.page_id)
        page = page_cache[comment.page_id]
        if page is not None and can_view_page(session, page, current_user):
            visible.append(comment)
    return visible


@router.post("/", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def add_comment(
    payload: CommentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page_or_404(session, payload.page_id)
    require_page_view(session, page, current_user)
    safe_payload = CommentCreate(
        page_id=page.id,
        block_id=payload.block_id,
        parent_comment_id=payload.parent_comment_id,
        body=payload.body,
        code=payload.code,
        language=payload.language,
    )
    try:
        return create_comment(session, safe_payload, author_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{comment_id}", response_model=CommentRead)
def get_comment(
    comment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    comment = _comment_or_404(session, comment_id)
    require_page_view(session, _page_or_404(session, comment.page_id), current_user)
    return comment


@router.patch("/{comment_id}", response_model=CommentRead)
def edit_comment(
    comment_id: int,
    payload: CommentUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    comment = _comment_or_404(session, comment_id)
    require_page_view(session, _page_or_404(session, comment.page_id), current_user)
    _require_comment_author(comment, current_user)
    try:
        return update_comment(session, comment, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.delete("/{comment_id}", response_model=CommentRead)
def remove_comment(
    comment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    comment = _comment_or_404(session, comment_id)
    require_page_view(session, _page_or_404(session, comment.page_id), current_user)
    _require_comment_author(comment, current_user)
    return delete_comment(session, comment)


# ── Interface HTMX: discussão geral da página ────────────────────────────────

@router.get("/pages/{page_id}/discussion", response_class=HTMLResponse)
def page_discussion(
    request: Request,
    page_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page_or_404(session, page_id)
    require_page_view(session, page, current_user)
    return _render_page_discussion(request, session, page, current_user)


@router.post("/pages/{page_id}/discussion", response_class=HTMLResponse, status_code=status.HTTP_201_CREATED)
def add_page_discussion_comment(
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
            CommentCreate(page_id=page.id, body=body, code=code or None, language=language or None),
            author_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _render_page_discussion(request, session, page, current_user)


@router.get("/{comment_id}/reply-form", response_class=HTMLResponse)
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
        raise HTTPException(status_code=422, detail="Comentário não disponível para resposta")
    block = session.get(PageBlock, comment.block_id) if comment.block_id is not None else None
    return templates.TemplateResponse(
        request=request,
        name="partials/comment_form.html",
        context={"page": page, "parent": comment, "block": block, "comment_languages": COMMENT_LANGUAGE_LABELS, "discussion_id": f"block-discussion-{block.id}" if block else f"page-discussion-{page.id}"},
    )


@router.post("/{comment_id}/replies", response_class=HTMLResponse, status_code=status.HTTP_201_CREATED)
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
        create_comment(session, CommentCreate(page_id=page.id, block_id=parent.block_id, parent_comment_id=parent.id, body=body, code=code or None, language=language or None), author_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _render_discussion(request, session, page, current_user, session.get(PageBlock, parent.block_id) if parent.block_id is not None else None)


@router.get("/{comment_id}/edit-form", response_class=HTMLResponse)
def edit_discussion_form(
    request: Request,
    comment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    comment = _comment_or_404(session, comment_id)
    page = _page_or_404(session, comment.page_id)
    require_page_view(session, page, current_user)
    _require_comment_author(comment, current_user)
    if comment.is_deleted:
        raise HTTPException(status_code=422, detail="Comentário não disponível para edição")
    block = session.get(PageBlock, comment.block_id) if comment.block_id is not None else None
    return templates.TemplateResponse(
        request=request,
        name="partials/comment_form.html",
        context={"page": page, "editing_comment": comment, "block": block, "comment_languages": COMMENT_LANGUAGE_LABELS, "discussion_id": f"block-discussion-{block.id}" if block else f"page-discussion-{page.id}"},
    )


@router.patch("/{comment_id}/discussion", response_class=HTMLResponse)
def update_discussion_comment(
    request: Request,
    comment_id: int,
    body: str = Form(""),
    code: str = Form(""),
    language: str = Form(""),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    comment = _comment_or_404(session, comment_id)
    page = _page_or_404(session, comment.page_id)
    require_page_view(session, page, current_user)
    _require_comment_author(comment, current_user)
    try:
        update_comment(session, comment, CommentUpdate(body=body, code=code or None, language=language or None))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _render_discussion(request, session, page, current_user, session.get(PageBlock, comment.block_id) if comment.block_id is not None else None)


@router.delete("/{comment_id}/discussion", response_class=HTMLResponse)
def remove_discussion_comment(
    request: Request,
    comment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    comment = _comment_or_404(session, comment_id)
    page = _page_or_404(session, comment.page_id)
    require_page_view(session, page, current_user)
    _require_comment_author(comment, current_user)
    delete_comment(session, comment)
    return _render_discussion(request, session, page, current_user, session.get(PageBlock, comment.block_id) if comment.block_id is not None else None)


# ── Interface HTMX: discussões de bloco ─────────────────────────────────────

@router.get("/blocks/{block_id}/discussion", response_class=HTMLResponse)
def block_discussion(
    request: Request,
    block_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    block = _block_or_404(session, block_id)
    page = _page_or_404(session, block.page_id)
    require_page_view(session, page, current_user)
    return _render_discussion(request, session, page, current_user, block)


@router.post("/blocks/{block_id}/discussion", response_class=HTMLResponse, status_code=status.HTTP_201_CREATED)
def add_block_discussion_comment(
    request: Request,
    block_id: int,
    body: str = Form(...),
    code: str = Form(""),
    language: str = Form(""),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    block = _block_or_404(session, block_id)
    page = _page_or_404(session, block.page_id)
    require_page_view(session, page, current_user)
    try:
        create_comment(session, CommentCreate(page_id=page.id, block_id=block.id, body=body, code=code or None, language=language or None), author_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _render_discussion(request, session, page, current_user, block)
