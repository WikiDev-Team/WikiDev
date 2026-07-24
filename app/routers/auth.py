from __future__ import annotations

from datetime import datetime, timedelta
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from ..config import get_settings
from ..crud import create_user
from ..db import get_session
from ..mailer import send_password_reset_email
from ..models import PasswordResetToken, User, UserCreate
from ..security import (
    generate_password_reset_token,
    generate_session_token,
    get_password_hash,
    hash_token,
    verify_password,
)
from ..templates import templates

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])


def _message_html(message: str, *, error: bool = False) -> HTMLResponse:
    css_class = "error-message" if error else "success-message"
    return HTMLResponse(f'<div class="{css_class}">{message}</div>')


def redirect_htmx(request: Request, url: str, token: str | None = None):
    if request.headers.get("HX-Request"):
        response = HTMLResponse(content="")
        response.headers["HX-Redirect"] = url
    else:
        response = RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)

    if token is not None:
        settings = get_settings()
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
            path="/",
            max_age=60 * 60 * 24 * 7,
        )
    return response


@router.get("/register", response_class=HTMLResponse)
def registration_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"project": "WikiDev"},
    )


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    username = username.strip()
    user = session.exec(select(User).where(User.username == username)).first()

    if not user or not verify_password(password, user.hashed_password):
        return _message_html("Usuário ou senha inválidos.", error=True)

    token = generate_session_token()
    user.token = hash_token(token)
    user.updated_at = datetime.utcnow()
    session.add(user)
    session.commit()
    return redirect_htmx(request, "/dashboard", token)


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    display_name: str = Form(""),
    session: Session = Depends(get_session),
):
    username = username.strip()
    email = email.strip().lower()
    display_name = display_name.strip()

    if not username or not email or not password:
        return _message_html("Preencha todos os campos obrigatórios.", error=True)
    if len(password) < 6:
        return _message_html("A senha deve ter pelo menos 6 caracteres.", error=True)
    if len(password.encode("utf-8")) > 72:
        return _message_html("A senha é longa demais.", error=True)
    if password != password_confirm:
        return _message_html("As senhas não coincidem.", error=True)
    if session.exec(select(User).where(User.username == username)).first():
        return _message_html("Nome de usuário já cadastrado.", error=True)
    if session.exec(select(User).where(User.email == email)).first():
        return _message_html("E-mail já cadastrado.", error=True)

    create_user(
        session,
        UserCreate(
            username=username,
            email=email,
            display_name=display_name,
            password=password,
        ),
    )
    return redirect_htmx(request, "/login?registered=1")


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="forgot_password.html",
        context={"project": "WikiDev"},
    )


@router.post("/forgot-password", response_class=HTMLResponse)
def request_password_reset(
    request: Request,
    email: str = Form(...),
    session: Session = Depends(get_session),
):
    email = email.strip().lower()
    user = session.exec(select(User).where(User.email == email)).first()

    if user is not None:
        now = datetime.utcnow()
        existing_tokens = session.exec(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        ).all()
        for existing in existing_tokens:
            existing.used_at = now
            session.add(existing)

        raw_token = generate_password_reset_token()
        settings = get_settings()
        reset = PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now + timedelta(minutes=settings.password_reset_ttl_minutes),
        )
        session.add(reset)
        session.commit()

        reset_url = f"{settings.app_base_url}/reset-password?token={raw_token}"
        try:
            send_password_reset_email(
                to_email=user.email,
                username=user.display_name or user.username,
                reset_url=reset_url,
                settings=settings,
            )
        except Exception:
            logger.exception("Falha ao enviar e-mail de recuperação")

    generic_message = (
        "Se o e-mail estiver cadastrado, você receberá as instruções de recuperação."
    )
    if request.headers.get("HX-Request"):
        return _message_html(generic_message)
    return templates.TemplateResponse(
        request=request,
        name="forgot_password.html",
        context={"project": "WikiDev", "message": generic_message},
    )


def _valid_reset_token(session: Session, raw_token: str) -> PasswordResetToken | None:
    token = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_token(raw_token)
        )
    ).first()
    if token is None or token.used_at is not None:
        return None
    if token.expires_at <= datetime.utcnow():
        return None
    return token


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(
    request: Request,
    token: str,
    session: Session = Depends(get_session),
):
    valid = _valid_reset_token(session, token) is not None
    return templates.TemplateResponse(
        request=request,
        name="reset_password.html",
        context={"project": "WikiDev", "token": token, "valid": valid},
        status_code=200 if valid else 400,
    )


@router.post("/reset-password", response_class=HTMLResponse)
def reset_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    session: Session = Depends(get_session),
):
    reset = _valid_reset_token(session, token)
    if reset is None:
        return _message_html("Este link é inválido ou expirou.", error=True)
    if len(password) < 6:
        return _message_html("A senha deve ter pelo menos 6 caracteres.", error=True)
    if len(password.encode("utf-8")) > 72:
        return _message_html("A senha é longa demais.", error=True)
    if password != password_confirm:
        return _message_html("As senhas não coincidem.", error=True)

    user = session.get(User, reset.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    now = datetime.utcnow()
    user.hashed_password = get_password_hash(password)
    user.token = None
    user.updated_at = now
    reset.used_at = now
    session.add(user)
    session.add(reset)

    other_tokens = session.exec(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    ).all()
    for other in other_tokens:
        other.used_at = now
        session.add(other)

    session.commit()
    return redirect_htmx(request, "/login?reset=1")


@router.get("/dev-login")
def dev_login(session: Session = Depends(get_session)):
    settings = get_settings()
    if not settings.enable_dev_login or settings.app_env == "production":
        raise HTTPException(status_code=404, detail="Rota não encontrada")

    user = session.exec(select(User)).first()
    if not user:
        user = create_user(
            session,
            UserCreate(username="dev", email="dev@dev.com", password="dev123"),
        )

    token = generate_session_token()
    user.token = hash_token(token)
    session.add(user)
    session.commit()

    response = HTMLResponse(content="")
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 24 * 7,
    )
    response.headers["HX-Redirect"] = "/dashboard"
    return response


@router.post("/logout")
def logout(request: Request, session: Session = Depends(get_session)):
    token = request.cookies.get("session_token")
    if token:
        user = session.exec(select(User).where(User.token == hash_token(token))).first()
        if user:
            user.token = None
            user.updated_at = datetime.utcnow()
            session.add(user)
            session.commit()

    if request.headers.get("HX-Request"):
        response = HTMLResponse(content="")
        response.headers["HX-Redirect"] = "/login"
    else:
        response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="session_token", path="/")
    return response
