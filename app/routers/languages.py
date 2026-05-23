from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Language, LanguageCreate, LanguageRead, LanguageUpdate
from ..crud import create_language, update_language

router = APIRouter(prefix="/languages", tags=["languages"])


@router.get("/", response_model=list[LanguageRead])
def list_languages(session: Session = Depends(get_session)):
    return session.exec(select(Language).order_by(Language.name)).all()


@router.post("/", response_model=LanguageRead, status_code=201)
def add_language(payload: LanguageCreate, session: Session = Depends(get_session)):
    return create_language(session, payload)


@router.get("/{language_id}", response_model=LanguageRead)
def get_language(language_id: int, session: Session = Depends(get_session)):
    obj = session.get(Language, language_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Linguagem não encontrada")
    return obj


@router.patch("/{language_id}", response_model=LanguageRead)
def edit_language(language_id: int, payload: LanguageUpdate, session: Session = Depends(get_session)):
    obj = session.get(Language, language_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Linguagem não encontrada")
    return update_language(session, obj, payload)


@router.delete("/{language_id}", status_code=204)
def remove_language(language_id: int, session: Session = Depends(get_session)):
    obj = session.get(Language, language_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Linguagem não encontrada")
    session.delete(obj)
    session.commit()
