from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..crud import update_user
from ..db import get_session
from ..dependencies import get_current_user
from ..models import User, UserPublicRead, UserRead, UserUpdate
from ..templates import templates

router = APIRouter(prefix="/users", tags=["users"])


def _user_or_404(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserRead)
def edit_me(
    payload: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    if "username" in data:
        duplicate = session.exec(
            select(User).where(User.username == data["username"], User.id != current_user.id)
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Nome de usuário já utilizado")
    if "email" in data:
        duplicate = session.exec(
            select(User).where(User.email == data["email"], User.id != current_user.id)
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="E-mail já utilizado")
    return update_user(session, current_user, payload)


@router.get("/", response_model=list[UserPublicRead])
def list_users(
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    return session.exec(select(User).order_by(User.display_name, User.username)).all()


@router.get("/{user_id}/profile", response_class=HTMLResponse)
def public_profile(
    request: Request,
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user = _user_or_404(session, user_id)
    return templates.TemplateResponse(
        request=request,
        name="public_profile.html",
        context={"project": "WikiDev", "profile_user": user, "usuario": current_user},
    )


@router.get("/{user_id}", response_model=UserPublicRead)
def get_user(
    user_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(get_current_user),
):
    return _user_or_404(session, user_id)
