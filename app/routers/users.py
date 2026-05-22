from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import User, UserCreate, UserRead, UserUpdate
from ..crud import create_user, update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserRead])
def list_users(session: Session = Depends(get_session)):
    return session.exec(select(User).order_by(User.id)).all()


@router.post("/", response_model=UserRead, status_code=201)
def add_user(payload: UserCreate, session: Session = Depends(get_session)):
    return create_user(session, payload)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, session: Session = Depends(get_session)):
    obj = session.get(User, user_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return obj


@router.patch("/{user_id}", response_model=UserRead)
def edit_user(user_id: int, payload: UserUpdate, session: Session = Depends(get_session)):
    obj = session.get(User, user_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return update_user(session, obj, payload)


@router.delete("/{user_id}", status_code=204)
def remove_user(user_id: int, session: Session = Depends(get_session)):
    obj = session.get(User, user_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    session.delete(obj)
    session.commit()
