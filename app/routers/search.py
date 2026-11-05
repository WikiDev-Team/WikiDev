from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, or_, select

from ..db import get_session
from ..dependencies import get_current_user
from ..models import PageBlock, Tag, User
from ..permissions import accessible_folders, list_accessible_pages
from ..templates import templates

router = APIRouter(tags=["search"])


@router.get("/busca", response_class=HTMLResponse)
def search(
    request: Request,
    q: str = "",
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    query = q.strip()
    if len(query) < 2:
        return HTMLResponse("<div class='search-empty'>Digite pelo menos 2 caracteres...</div>")

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
        for page in list_accessible_pages(session, current_user.id)
        if normalized in page.title.casefold()
    ][:20]
    folders = [
        folder
        for folder in accessible_folders(session, current_user)
        if normalized in folder.name.casefold()
    ][:20]

    return templates.TemplateResponse(
        request=request,
        name="partials/search_results.html",
        context={
            "termo": query,
            "usuarios": users,
            "paginas": pages,
            "pastas": folders,
            "usuario_atual": current_user,
        },
    )


PALETTE_LIMIT = 8


@router.get("/busca/rapida", response_class=HTMLResponse)
def quick_search(
    request: Request,
    q: str = "",
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Resultados da paleta Ctrl+K: título primeiro, depois conteúdo dos blocos."""
    query = " ".join(q.split())
    pages = list_accessible_pages(session, current_user.id)

    if not query:
        recent = sorted(pages, key=lambda page: page.updated_at, reverse=True)[:PALETTE_LIMIT]
        return templates.TemplateResponse(
            request=request,
            name="partials/command_results.html",
            context={"query": "", "title_pages": recent, "content_pages": [], "folders": [], "tags": [], "users": []},
        )

    normalized = query.casefold()
    title_pages = [page for page in pages if normalized in page.title.casefold()][:PALETTE_LIMIT]
    title_ids = {page.id for page in title_pages}
    pages_by_id = {page.id: page for page in pages}

    content_pages = []
    if len(query) >= 3 and pages_by_id:
        matches = session.exec(
            select(PageBlock.page_id)
            .where(PageBlock.page_id.in_(list(pages_by_id)), PageBlock.content.ilike(f"%{query}%"))
            .distinct()
        ).all()
        content_pages = [
            pages_by_id[page_id] for page_id in matches if page_id not in title_ids
        ][:PALETTE_LIMIT]

    folders = [
        folder for folder in accessible_folders(session, current_user)
        if normalized in folder.name.casefold()
    ][:5]
    tags = session.exec(
        select(Tag).where(Tag.name.ilike(f"%{query}%")).order_by(Tag.name).limit(5)
    ).all()
    users = session.exec(
        select(User)
        .where(or_(User.username.ilike(f"%{query}%"), User.display_name.ilike(f"%{query}%")))
        .order_by(User.username)
        .limit(5)
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="partials/command_results.html",
        context={
            "query": query,
            "title_pages": title_pages,
            "content_pages": content_pages,
            "folders": folders,
            "tags": tags,
            "users": users,
        },
    )
