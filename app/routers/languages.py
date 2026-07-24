from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from ..crud import create_language, update_language
from ..db import get_session
from ..dependencies import get_current_user
from ..models import Language, LanguageCreate, LanguageRead, LanguageUpdate, Page, User

router = APIRouter(prefix="/languages", tags=["languages"])


def _language_or_404(session: Session, language_id: int) -> Language:
    language = session.get(Language, language_id)
    if language is None:
        raise HTTPException(status_code=404, detail="Linguagem não encontrada")
    return language


@router.get("/", response_model=list[LanguageRead])
def list_languages(session: Session = Depends(get_session)):
    return session.exec(select(Language).order_by(Language.name)).all()


@router.post("/", response_model=LanguageRead, status_code=status.HTTP_201_CREATED)
def add_language(
    payload: LanguageCreate,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    return create_language(session, payload)


@router.get("/{language_id}", response_model=LanguageRead)
def get_language(language_id: int, session: Session = Depends(get_session)):
    return _language_or_404(session, language_id)


@router.patch("/{language_id}", response_model=LanguageRead)
def edit_language(
    language_id: int,
    payload: LanguageUpdate,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    return update_language(session, _language_or_404(session, language_id), payload)


@router.delete("/{language_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_language(
    language_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    language = _language_or_404(session, language_id)
    if session.exec(select(Page).where(Page.language_id == language.id)).first():
        raise HTTPException(
            status_code=409,
            detail="A linguagem está vinculada a páginas e não pode ser excluída",
        )
    session.delete(language)
    session.commit()
