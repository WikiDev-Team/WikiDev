from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..crud import create_comment, update_comment
from ..db import get_session
from ..dependencies import get_current_user
from ..models import Comment, CommentCreate, CommentRead, CommentUpdate, Page, User
from ..permissions import list_accessible_pages, require_page_view

router = APIRouter(prefix="/comments", tags=["comments"])


def _page_or_404(session: Session, page_id: int) -> Page:
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return page


def _comment_or_404(session: Session, comment_id: int) -> Comment:
    comment = session.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comentário não encontrado")
    return comment


@router.get("/", response_model=list[CommentRead])
def list_comments(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    page_id: int | None = None,
):
    stmt = select(Comment).order_by(Comment.created_at)
    if page_id is not None:
        page = _page_or_404(session, page_id)
        require_page_view(session, page, current_user)
        stmt = stmt.where(Comment.page_id == page_id)
    else:
        accessible_ids = [page.id for page in list_accessible_pages(session, current_user.id)]
        if not accessible_ids:
            return []
        stmt = stmt.where(Comment.page_id.in_(accessible_ids))
    return session.exec(stmt).all()


@router.post("/", response_model=CommentRead, status_code=201)
def add_comment(
    payload: CommentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page_or_404(session, payload.page_id)
    require_page_view(session, page, current_user)
    safe_payload = payload.model_copy(update={"author_id": current_user.id})
    return create_comment(session, safe_payload)


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
    page = _page_or_404(session, comment.page_id)
    if comment.author_id != current_user.id and page.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não pode editar este comentário")
    return update_comment(session, comment, payload)


@router.delete("/{comment_id}", status_code=204)
def remove_comment(
    comment_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    comment = _comment_or_404(session, comment_id)
    page = _page_or_404(session, comment.page_id)
    if comment.author_id != current_user.id and page.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não pode excluir este comentário")
    session.delete(comment)
    session.commit()
