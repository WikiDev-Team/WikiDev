# app/routers/auth.py
from fastapi import APIRouter, Depends, Response, Form, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..db import get_session
from ..models import User
from ..security import verify_password, generate_session_token

router = APIRouter(tags=["auth"])

@router.post("/login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.username == username)).first()

    if not user or not verify_password(password, user.hashed_password):
        erro_html = '<div class="error-message" style="color: red; margin-top: 10px;">Usuário não encontrado.</div>'
        return HTMLResponse(content=erro_html, status_code=status.HTTP_401_UNAUTHORIZED)
    
    token = generate_session_token()
    user.token = token

    session.add(user)
    session.commit()

    resposta = HTMLResponse(content="")

    # define o cookie
    resposta.set_cookie(
        key="session_token",
        value=token,
        httponly=True,  
        secure=False,   # mudar para True em produção (HTTPS)
        samesite="lax",
        path="/"
    )
    
    resposta.headers["HX-Redirect"] = "/"

    return resposta

@router.get("/dev-login")
def dev_login(session: Session = Depends(get_session)):
    user = session.exec(select(User)).first()
    
    if not user:
        from ..crud import create_user
        from ..models import UserCreate
        user = create_user(session, UserCreate(
            username="dev",
            email="dev@dev.com",
            password="dev123"
        ))
    
    token = generate_session_token()
    user.token = token
    session.add(user)
    session.commit()

    resposta = HTMLResponse(content="")
    resposta.set_cookie(key="session_token", value=token, httponly=True)
    resposta.headers["HX-Redirect"] = "/dashboard"
    return resposta
