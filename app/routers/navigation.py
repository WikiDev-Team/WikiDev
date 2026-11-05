"""Rotas de navegação: árvore lateral sob demanda, favoritas e lista filtrada da home."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from ..db import get_session
from ..dependencies import get_current_user
from ..models import Folder, Page, User
from ..navigation import (
    SIDEBAR_FAVORITES,
    TREE_PAGE_SIZE,
    BrowseFilters,
    browse_pages,
    favorite_pages,
    folder_tree_pages,
    toggle_favorite,
    unfiled_tree_pages,
)
from ..permissions import can_view_folder, list_accessible_pages, require_page_view
from ..templates import templates

router = APIRouter(tags=["navigation"])


def _tree_slice(request: Request, user: User, pages: list[Page], offset: int, more_url: str):
    offset = max(0, offset)
    end = offset + TREE_PAGE_SIZE
    return templates.TemplateResponse(
        request=request,
        name="partials/nav/tree_pages.html",
        context={
            "usuario": user,
            "tree_items": pages[offset:end],
            "next_offset": end if end < len(pages) else None,
            "remaining": max(0, len(pages) - end),
            "more_url": more_url,
        },
    )


@router.get("/nav/pastas/{folder_id}", response_class=HTMLResponse)
def tree_folder_pages(
    request: Request,
    folder_id: int,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = session.get(Folder, folder_id)
    if folder is None or not can_view_folder(session, folder, current_user):
        raise HTTPException(status_code=404, detail="Pasta não encontrada")
    pages = folder_tree_pages(session, current_user, folder)
    return _tree_slice(request, current_user, pages, offset, f"/nav/pastas/{folder.id}")


@router.get("/nav/sem-pasta", response_class=HTMLResponse)
def tree_unfiled_pages(
    request: Request,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pages = unfiled_tree_pages(session, current_user)
    return _tree_slice(request, current_user, pages, offset, "/nav/sem-pasta")


@router.post("/pages/{page_id}/favorite", response_class=HTMLResponse)
def toggle_page_favorite(
    request: Request,
    page_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    require_page_view(session, page, current_user)
    favorite = toggle_favorite(session, current_user.id, page.id)
    visible = {item.id: item for item in list_accessible_pages(session, current_user.id)}
    return templates.TemplateResponse(
        request=request,
        name="partials/nav/favorite_toggle.html",
        context={
            "page": page,
            "is_favorite": favorite,
            "sidebar_favorites": favorite_pages(session, current_user.id, visible)[:SIDEBAR_FAVORITES],
            "favorites_oob": True,
        },
    )


@router.get("/home/paginas", response_class=HTMLResponse)
def home_pages(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Lista filtrada da home. Com offset devolve só as próximas linhas (Mostrar mais)."""
    filters = BrowseFilters.from_params(request.query_params)
    pages = list_accessible_pages(session, current_user.id)
    context = {"usuario": current_user, **browse_pages(session, current_user, pages, filters)}
    if filters.offset:
        return templates.TemplateResponse(
            request=request, name="partials/nav/browse_rows.html", context=context
        )
    query = filters.query_string()
    return templates.TemplateResponse(
        request=request,
        name="partials/nav/browse_results.html",
        context=context,
        headers={"HX-Replace-Url": "/dashboard" + (f"?{query}" if query else "")},
    )
