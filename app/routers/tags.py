from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..crud import create_tag, update_tag
from ..db import get_session
from ..dependencies import get_current_user
from ..models import PageTagLink, Tag, TagCreate, TagRead, TagUpdate, User

router = APIRouter(prefix="/tags", tags=["tags"])


def _tag_or_404(session: Session, tag_id: int) -> Tag:
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag não encontrada")
    return tag


@router.get("/", response_model=list[TagRead])
def list_tags(session: Session = Depends(get_session)):
    return session.exec(select(Tag).order_by(Tag.name)).all()


@router.post("/", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def add_tag(
    payload: TagCreate,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    return create_tag(session, payload)


@router.get("/{tag_id}", response_model=TagRead)
def get_tag(tag_id: int, session: Session = Depends(get_session)):
    return _tag_or_404(session, tag_id)


@router.patch("/{tag_id}", response_model=TagRead)
def edit_tag(
    tag_id: int,
    payload: TagUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    return update_tag(session, _tag_or_404(session, tag_id), payload)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_tag(
    tag_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    tag = _tag_or_404(session, tag_id)
    if session.exec(select(PageTagLink).where(PageTagLink.tag_id == tag.id)).first():
        raise HTTPException(
            status_code=409,
            detail="A tag está vinculada a páginas e não pode ser excluída",
        )
    session.delete(tag)
    session.commit()
