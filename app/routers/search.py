# app/routers/search.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, or_

from ..db import get_session
from ..models import Page, PageStatus, User
from ..dependencies import get_current_user

router = APIRouter(tags=["search"])
templates = Jinja2Templates(directory="templates")

@router.get("/busca", response_class=HTMLResponse)
def buscar_global_htmx(
    request: Request,
    q: str = "",
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Evita buscas pesadas com apenas 1 caractere
    if len(q.strip()) < 2:
        return HTMLResponse("<div class='text-gray-500 text-sm'>Digite pelo menos 2 caracteres...</div>")

    termo = f"%{q.strip()}%"

    # 1. Busca de Usuários
    stmt_users = select(User).where(
        or_(
            User.username.ilike(termo),
            User.display_name.ilike(termo)
        )
    ).order_by(User.display_name).limit(10)
    usuarios = session.exec(stmt_users).all()

    # 2. Busca de Páginas (Públicas ou do próprio autor)
    stmt_pages = select(Page).where(
        Page.title.ilike(termo)
    ).where(
        or_(
            Page.status == PageStatus.PUBLISHED,
            Page.author_id == current_user.id
        )
    ).order_by(Page.title).limit(20)
    paginas = session.exec(stmt_pages).all()

    return templates.TemplateResponse(
        request=request,
        name="partials/search_results.html",
        context={
            "usuarios": usuarios,
            "paginas": paginas,
            "termo": q,
            "usuario_atual": current_user
        }
    )
