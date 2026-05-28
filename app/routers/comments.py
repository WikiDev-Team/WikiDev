from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Comment, CommentCreate, CommentRead, CommentUpdate
from ..crud import create_comment, update_comment

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("/", response_model=list[CommentRead])
def list_comments(session: Session = Depends(get_session), page_id: int | None = None):
    stmt = select(Comment).order_by(Comment.created_at)
    if page_id is not None:
        stmt = stmt.where(Comment.page_id == page_id)
    return session.exec(stmt).all()


@router.post("/", response_model=CommentRead, status_code=201)
def add_comment(payload: CommentCreate, session: Session = Depends(get_session)):
    return create_comment(session, payload)


@router.get("/{comment_id}", response_model=CommentRead)
def get_comment(comment_id: int, session: Session = Depends(get_session)):
    obj = session.get(Comment, comment_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Comentário não encontrado")
    return obj


@router.patch("/{comment_id}", response_model=CommentRead)
def edit_comment(comment_id: int, payload: CommentUpdate, session: Session = Depends(get_session)):
    obj = session.get(Comment, comment_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Comentário não encontrado")
    return update_comment(session, obj, payload)


@router.delete("/{comment_id}", status_code=204)
def remove_comment(comment_id: int, session: Session = Depends(get_session)):
    obj = session.get(Comment, comment_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Comentário não encontrado")
    session.delete(obj)
    session.commit()
