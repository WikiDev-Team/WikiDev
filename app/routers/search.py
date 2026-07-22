from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, or_, select

from ..db import get_session
from ..dependencies import get_current_user
from ..models import User
from ..permissions import accessible_pages
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

    pattern = f"%{query}%"
    users = session.exec(
        select(User)
        .where(or_(User.username.ilike(pattern), User.display_name.ilike(pattern)))
        .order_by(User.display_name, User.username)
        .limit(10)
    ).all()

    normalized = query.casefold()
    pages = [
        page
        for page in accessible_pages(session, current_user)
        if normalized in page.title.casefold()
    ][:20]

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
