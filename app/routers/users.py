from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..crud import create_user, update_user
from ..db import get_session
from ..dependencies import get_current_user
from ..models import User, UserCreate, UserPublicRead, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserPublicRead])
def list_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return session.exec(select(User).order_by(User.id)).all()


@router.post("/", response_model=UserRead, status_code=201)
def add_user(payload: UserCreate, session: Session = Depends(get_session)):
    return create_user(session, payload)


@router.get("/{user_id}", response_model=UserPublicRead)
def get_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    obj = session.get(User, user_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return obj


@router.patch("/{user_id}", response_model=UserRead)
def edit_user(
    user_id: int,
    payload: UserUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você só pode editar o próprio perfil")
    return update_user(session, current_user, payload)


@router.delete("/{user_id}", status_code=204)
def remove_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você só pode excluir a própria conta")
    session.delete(current_user)
    session.commit()
