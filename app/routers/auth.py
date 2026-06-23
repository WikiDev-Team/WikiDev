# app/routers/auth.py
from fastapi import APIRouter, Depends, Response, Form, status, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from ..db import get_session
from ..models import User, UserCreate
from ..crud import create_user
from ..security import verify_password, generate_session_token

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="templates")

#para realmente salvar o registro
def redirect_htmx(request: Request, url: str, token: str | None = None):
    if request.headers.get("HX-Request"):
        resposta = HTMLResponse(content="")
        resposta.headers["HX-Redirect"] = url
    else:
        resposta = RedirectResponse(
            url=url,
            status_code=status.HTTP_303_SEE_OTHER
        )

    if token is not None:
        resposta.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/"
        )

    return resposta

@router.get("/register", response_class=HTMLResponse)
async def tela_cadastro(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"project": "WikiDev"}
    )

@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.username == username)).first()

    if not user or not verify_password(password, user.hashed_password):
        erro_html = """
        <div class="error-message" style="color: red; margin-top: 10px;">
            Usuário ou senha inválidos.
        </div>
        """
        return HTMLResponse(content=erro_html, status_code=200)
    
    token = generate_session_token()
    user.token = token

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
    session: Session = Depends(get_session)
):
    username = username.strip()
    email = email.strip().lower()
    display_name = display_name.strip()

    def erro_cadastro(mensagem: str):
        return HTMLResponse(
            content=f'''
            <div class="error-message" style="color: red; margin-top: 10px;">
                {mensagem}
            </div>
            ''',
            status_code=200
        )

    if not username or not email or not password:
        return erro_cadastro("Preencha todos os campos obrigatórios.")

    if len(password) < 6:
        return erro_cadastro("A senha deve ter pelo menos 6 caracteres.")

    if password != password_confirm:
        return erro_cadastro("As senhas não coincidem.")

    usuario_existente = session.exec(
        select(User).where(User.username == username)
    ).first()

    if usuario_existente:
        return erro_cadastro("Nome de usuário já cadastrado.")

    email_existente = session.exec(
        select(User).where(User.email == email)
    ).first()

    if email_existente:
        return erro_cadastro("E-mail já cadastrado.")

    create_user(
        session,
        UserCreate(
            username=username,
            email=email,
            display_name=display_name,
            password=password
        )
    )

    return redirect_htmx(request, "/login?registered=1")

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

@router.post("/logout")
def logout(request: Request):
    if request.headers.get("HX-Request"):
        resposta = HTMLResponse(content="")
        resposta.headers["HX-Redirect"] = "/login"
    else:
        resposta = RedirectResponse(
            url="/login",
            status_code=status.HTTP_303_SEE_OTHER
        )

    resposta.delete_cookie(
        key="session_token",
        path="/"
    )

    return resposta