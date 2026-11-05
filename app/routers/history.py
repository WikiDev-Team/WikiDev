from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from ..db import get_session
from ..dependencies import get_current_user
from ..models import Page, PageRevision, User
from ..permissions import can_edit_page, require_page_edit, require_page_view
from ..revisions import diff_revisions, list_revisions, previous_revision, restore_revision
from ..navigation import visible_folder_path
from ..templates import templates
from .page_blocks import page_view_context

router = APIRouter(prefix="/pages", tags=["history"])


def _page(session: Session, page_id: int) -> Page:
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return page


def _revision(session: Session, page: Page, revision_id: int) -> PageRevision:
    revision = session.get(PageRevision, revision_id)
    if revision is None or revision.page_id != page.id:
        raise HTTPException(status_code=404, detail="Versão não encontrada")
    return revision


def history_context(
    session: Session, page: Page, current_user: User, selected_id: int | None = None
) -> dict:
    revisions = list_revisions(session, page.id)
    selected = next((item for item in revisions if item.id == selected_id), None)
    if selected is None and revisions:
        selected = revisions[0]
    authors = {
        revision.author_id: session.get(User, revision.author_id)
        for revision in revisions
        if revision.author_id is not None
    }
    diff = None
    if selected is not None:
        diff = diff_revisions(previous_revision(session, selected), selected)
    return {
        "page": page,
        "revisions": revisions,
        "selected_revision": selected,
        "is_latest": bool(revisions) and selected is revisions[0],
        "diff": diff,
        "revision_authors": authors,
        "can_edit": can_edit_page(session, page, current_user),
        "folder_path": visible_folder_path(session, page.folder, current_user),
    }


@router.get("/{page_id}/history", response_class=HTMLResponse)
def page_history(
    request: Request,
    page_id: int,
    v: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page(session, page_id)
    require_page_view(session, page, current_user)
    return templates.TemplateResponse(
        request=request,
        name="partials/page_history.html",
        context=history_context(session, page, current_user, v),
    )


@router.post("/{page_id}/history/{revision_id}/restore", response_class=HTMLResponse)
def restore_page_revision(
    request: Request,
    page_id: int,
    revision_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page(session, page_id)
    require_page_edit(session, page, current_user)
    revision = _revision(session, page, revision_id)
    restore_revision(session, page, revision, current_user)
    session.refresh(page)
    return templates.TemplateResponse(
        request=request,
        name="partials/page_blocks_editor.html",
        context={**page_view_context(session, page, current_user), "restored": True},
        headers={"HX-Push-Url": f"/p/{page.id}"},
    )
