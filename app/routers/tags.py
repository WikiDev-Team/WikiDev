from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Tag, TagCreate, TagRead, TagUpdate
from ..crud import create_tag, update_tag

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=list[TagRead])
def list_tags(session: Session = Depends(get_session)):
    return session.exec(select(Tag).order_by(Tag.name)).all()


@router.post("/", response_model=TagRead, status_code=201)
def add_tag(payload: TagCreate, session: Session = Depends(get_session)):
    return create_tag(session, payload)


@router.get("/{tag_id}", response_model=TagRead)
def get_tag(tag_id: int, session: Session = Depends(get_session)):
    obj = session.get(Tag, tag_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Tag não encontrada")
    return obj


@router.patch("/{tag_id}", response_model=TagRead)
def edit_tag(tag_id: int, payload: TagUpdate, session: Session = Depends(get_session)):
    obj = session.get(Tag, tag_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Tag não encontrada")
    return update_tag(session, obj, payload)


@router.delete("/{tag_id}", status_code=204)
def remove_tag(tag_id: int, session: Session = Depends(get_session)):
    obj = session.get(Tag, tag_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Tag não encontrada")
    session.delete(obj)
    session.commit()
