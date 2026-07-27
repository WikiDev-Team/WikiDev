from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..crud import create_comment, delete_comment, update_comment
from ..db import get_session
from ..dependencies import get_current_user
from ..models import Comment, CommentCreate, CommentRead, CommentUpdate, Page, User
from ..permissions import can_view_page, require_page_view

router = APIRouter(prefix="/comments", tags=["comments"])


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


def _require_comment_author(comment: Comment, current_user: User) -> None:
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não pode alterar este comentário")


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
