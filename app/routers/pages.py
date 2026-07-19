from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..crud import count_active_comments_by_block, create_page, update_page
from ..db import get_session
from ..dependencies import get_current_user
from ..models import (
    Page,
    PageBlock,
    PageCreate,
    PageRead,
    PageStatus,
    PageTagLink,
    PageType,
    PageUpdate,
    PageVisibility,
    User,
)
from ..permissions import (
    accessible_pages_query,
    can_edit_page,
    get_friend_users,
    get_page_share_user_ids,
    list_accessible_pages,
    replace_page_shares,
    require_page_edit,
    require_page_owner,
)
from ..templates import templates

router = APIRouter(prefix="/pages", tags=["pages"])


def _page_or_404(session: Session, page_id: int) -> Page:
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return page


def _sidebar_context(session: Session, current_user: User) -> dict:
    pages = list_accessible_pages(session, current_user.id)
    editable_page_ids = {
        page.id for page in pages if can_edit_page(session, page, current_user)
    }
    return {"pages": pages, "editable_page_ids": editable_page_ids, "usuario": current_user}


@router.get("/", response_model=list[PageRead])
def list_pages(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    language_id: int | None = None,
    page_type: str | None = None,
    status: str | None = None,
    folder_id: int | None = None,
    tag_id: int | None = None,
    q: str | None = None,
):
    """Lista somente páginas que o usuário atual pode visualizar."""
    stmt = accessible_pages_query(session, current_user.id).order_by(Page.created_at.desc())
    if language_id is not None:
        stmt = stmt.where(Page.language_id == language_id)
    if page_type is not None:
        stmt = stmt.where(Page.page_type == page_type)
    if status is not None:
        stmt = stmt.where(Page.status == status)
    if folder_id is not None:
        stmt = stmt.where(Page.folder_id == folder_id)
    if tag_id is not None:
        stmt = stmt.join(PageTagLink).where(PageTagLink.tag_id == tag_id)
    if q:
        stmt = stmt.where(Page.title.ilike(f"%{q}%"))
    return session.exec(stmt).unique().all()


@router.post("/", response_class=HTMLResponse)
def add_page_htmx(
    request: Request,
    title: str = Form(...),
    summary: str = Form(""),
    page_type: PageType = Form(PageType.NOTE),
    status: PageStatus = Form(PageStatus.DRAFT),
    visibility: PageVisibility = Form(PageVisibility.PRIVATE),
    tag_ids: str = Form(""),
    shared_user_ids: list[int] | None = Form(None),
    editor_user_ids: list[int] | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    parsed_tag_ids = [
        int(tag_id.strip())
        for tag_id in tag_ids.split(",")
        if tag_id.strip().isdigit()
    ]

    payload = PageCreate(
        title=title,
        summary=summary,
        page_type=page_type,
        status=status,
        visibility=visibility,
        author_id=current_user.id,
        tag_ids=parsed_tag_ids,
    )
    page = create_page(session, payload)

    replace_page_shares(
        session,
        page,
        current_user.id,
        shared_user_ids or [],
        editor_user_ids or [],
    )
    session.commit()

    context = {
        "page": page,
        "blocks": [],
        "can_edit": True,
        "is_owner": True,
        **_sidebar_context(session, current_user),
    }
    return templates.TemplateResponse(
        request=request,
        name="partials/page_response.html",
        context=context,
    )


@router.delete("/{page_id}", status_code=204)
def remove_page(
    page_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page_or_404(session, page_id)
    require_page_owner(page, current_user)
    session.delete(page)
    session.commit()


@router.get("/new", response_class=HTMLResponse)
def new_page_form(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        request=request,
        name="partials/page_create.html",
        context={"friends": get_friend_users(session, current_user.id)},
    )


@router.patch("/{page_id}", response_class=HTMLResponse)
def edit_page(
    request: Request,
    page_id: int,
    title: str = Form(...),
    summary: str = Form(""),
    page_type: PageType = Form(PageType.NOTE),
    status: PageStatus = Form(PageStatus.DRAFT),
    visibility: PageVisibility | None = Form(None),
    shared_user_ids: list[int] | None = Form(None),
    editor_user_ids: list[int] | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page_or_404(session, page_id)
    require_page_edit(session, page, current_user)
    is_owner = page.author_id == current_user.id

    payload = PageUpdate(
        title=title,
        summary=summary,
        page_type=page_type,
        status=status,
        visibility=visibility if is_owner and visibility is not None else None,
    )
    page = update_page(session, page, payload)

    if is_owner:
        replace_page_shares(
            session,
            page,
            current_user.id,
            shared_user_ids or [],
            editor_user_ids or [],
        )
        session.commit()

    blocks = session.exec(
        select(PageBlock)
        .where(PageBlock.page_id == page.id)
        .order_by(PageBlock.position.asc(), PageBlock.id.asc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="partials/page_response.html",
        context={
            "page": page,
            "blocks": blocks,
            "block_comment_counts": count_active_comments_by_block(
                session, [block.id for block in blocks]
            ),
            "can_edit": True,
            "is_owner": is_owner,
            **_sidebar_context(session, current_user),
        },
    )


@router.get("/{page_id}/metadata/edit", response_class=HTMLResponse)
def edit_page_metadata_form(
    request: Request,
    page_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page_or_404(session, page_id)
    require_page_edit(session, page, current_user)
    is_owner = page.author_id == current_user.id
    shared_user_ids, editor_user_ids = get_page_share_user_ids(session, page.id)

    return templates.TemplateResponse(
        request=request,
        name="partials/page_metadata_form.html",
        context={
            "page": page,
            "is_owner": is_owner,
            "friends": get_friend_users(session, current_user.id) if is_owner else [],
            "shared_user_ids": shared_user_ids,
            "editor_user_ids": editor_user_ids,
        },
    )
