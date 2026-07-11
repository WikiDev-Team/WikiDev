from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, or_, select

from ..db import get_session
from ..dependencies import get_current_user
from ..models import Page, User
from ..permissions import accessible_pages_query
from ..templates import templates

router = APIRouter(tags=["search"])


@router.get("/busca", response_class=HTMLResponse)
def buscar_global_htmx(
    request: Request,
    q: str = "",
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = q.strip()
    if len(query) < 2:
        return HTMLResponse(
            "<div class='search-empty'>Digite pelo menos 2 caracteres...</div>"
        )

    term = f"%{query}%"
    users = session.exec(
        select(User)
        .where(
            or_(
                User.username.ilike(term),
                User.display_name.ilike(term),
            )
        )
        .order_by(User.display_name, User.username)
        .limit(10)
    ).all()

    pages_stmt = (
        accessible_pages_query(session, current_user.id)
        .where(Page.title.ilike(term))
        .order_by(Page.title)
        .limit(20)
    )
    pages = session.exec(pages_stmt).unique().all()

    return templates.TemplateResponse(
        request=request,
        name="partials/search_results.html",
        context={
            "usuarios": users,
            "paginas": pages,
            "termo": query,
            "usuario_atual": current_user,
        },
    )
