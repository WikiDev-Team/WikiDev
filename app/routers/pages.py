from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from sqlmodel import Session, select

from ..crud import create_page, delete_page, update_page
from ..db import get_session
from ..dependencies import get_current_user
from ..models import (
    Folder,
    EditPolicy,
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
    accessible_folders,
    can_edit_page,
    get_friend_users,
    get_page_share_user_ids,
    list_accessible_pages,
    replace_page_shares,
    require_folder_edit,
    require_page_edit,
    require_page_owner,
    require_page_view,
)
from ..templates import templates

router = APIRouter(prefix="/pages", tags=["pages"])


def _page_or_404(session: Session, page_id: int) -> Page:
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return page


def _parse_tag_ids(value: str) -> list[int]:
    result: list[int] = []
    for raw in value.split(","):
        raw = raw.strip()
        if not raw:
            continue
        if not raw.isdigit():
            raise HTTPException(status_code=422, detail="IDs de tags devem ser números")
        result.append(int(raw))
    return result


def _parse_folder_id(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    if not value.strip().isdigit():
        raise HTTPException(status_code=422, detail="Pasta inválida")
    return int(value)


def _owned_folders(session: Session, current_user: User) -> list[Folder]:
    return session.exec(
        select(Folder).where(Folder.author_id == current_user.id).order_by(Folder.name)
    ).all()


def _blocks(session: Session, page_id: int) -> list[PageBlock]:
    return session.exec(
        select(PageBlock)
        .where(PageBlock.page_id == page_id)
        .order_by(PageBlock.position.asc(), PageBlock.id.asc())
    ).all()


def _sidebar_context(session: Session, current_user: User) -> dict:
    pages = list_accessible_pages(session, current_user.id)
    return {
        "pages": pages,
        "editable_page_ids": {
            page.id for page in pages if can_edit_page(session, page, current_user)
        },
        "folders": accessible_folders(session, current_user),
        "owned_folders": _owned_folders(session, current_user),
        "usuario": current_user,
    }


@router.get("/", response_model=list[PageRead])
def list_pages(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    language_id: int | None = None,
    page_type: str | None = None,
    page_status: str | None = Query(default=None, alias="status"),
    folder_id: int | None = None,
    tag_id: int | None = None,
    q: str | None = None,
):
    pages = list_accessible_pages(session, current_user.id)
    if language_id is not None:
        pages = [page for page in pages if page.language_id == language_id]
    if page_type is not None:
        pages = [page for page in pages if page.page_type.value == page_type]
    if page_status is not None:
        pages = [page for page in pages if page.status.value == page_status]
    if folder_id is not None:
        pages = [page for page in pages if page.folder_id == folder_id]
    if tag_id is not None:
        tagged_page_ids = {
            row.page_id
            for row in session.exec(
                select(PageTagLink).where(PageTagLink.tag_id == tag_id)
            ).all()
        }
        pages = [page for page in pages if page.id in tagged_page_ids]
    if q:
        normalized = q.casefold()
        pages = [page for page in pages if normalized in page.title.casefold()]
    return pages


@router.post("/", response_class=HTMLResponse)
def add_page_htmx(
    request: Request,
    title: str = Form(...),
    summary: str = Form(""),
    page_type: PageType = Form(PageType.NOTE),
    status: PageStatus = Form(PageStatus.DRAFT),
    visibility: PageVisibility = Form(PageVisibility.PRIVATE),
    edit_policy: EditPolicy = Form(EditPolicy.OWNER),
    tag_ids: str = Form(""),
    folder_id: str = Form(""),
    shared_user_ids: list[int] | None = Form(None),
    editor_user_ids: list[int] | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    cleaned_title = title.strip()
    if not cleaned_title:
        raise HTTPException(status_code=422, detail="O título é obrigatório")

    parsed_folder_id = _parse_folder_id(folder_id)
    if parsed_folder_id is not None:
        folder = session.get(Folder, parsed_folder_id)
        if folder is None:
            raise HTTPException(status_code=404, detail="Pasta não encontrada")
        require_folder_edit(folder, current_user)

    if visibility == PageVisibility.PRIVATE:
        edit_policy = EditPolicy.OWNER
    elif editor_user_ids and edit_policy == EditPolicy.OWNER:
        # Mantém compatibilidade com formulários antigos que já enviavam
        # editores antes de a política ser um campo separado.
        edit_policy = EditPolicy.CUSTOM

    page = create_page(
        session,
        PageCreate(
            title=cleaned_title,
            summary=summary.strip(),
            page_type=page_type,
            status=status,
            visibility=visibility,
            edit_policy=edit_policy,
            author_id=current_user.id,
            folder_id=parsed_folder_id,
            tag_ids=_parse_tag_ids(tag_ids),
        ),
    )
    replace_page_shares(
        session,
        page,
        current_user.id,
        shared_user_ids or [],
        editor_user_ids or [],
    )
    session.commit()

    return templates.TemplateResponse(
        request=request,
        name="partials/page_response.html",
        context={
            "page": page,
            "blocks": [],
            "can_edit": True,
            "is_owner": True,
            **_sidebar_context(session, current_user),
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_page_form(
    request: Request,
    folder_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if folder_id is not None:
        folder = session.get(Folder, folder_id)
        if folder is None:
            raise HTTPException(status_code=404, detail="Pasta não encontrada")
        require_folder_edit(folder, current_user)
    return templates.TemplateResponse(
        request=request,
        name="partials/page_create.html",
        context={
            "friends": get_friend_users(session, current_user.id),
            "owned_folders": _owned_folders(session, current_user),
            "selected_folder_id": folder_id,
        },
    )


@router.get("/{page_id}", response_model=PageRead)
def get_page(
    page_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page_or_404(session, page_id)
    require_page_view(session, page, current_user)
    return page


@router.patch("/{page_id}", response_class=HTMLResponse)
def edit_page(
    request: Request,
    page_id: int,
    title: str = Form(...),
    summary: str = Form(""),
    page_type: PageType = Form(PageType.NOTE),
    status: PageStatus = Form(PageStatus.DRAFT),
    visibility: PageVisibility | None = Form(None),
    edit_policy: EditPolicy | None = Form(None),
    folder_id: str | None = Form(None),
    shared_user_ids: list[int] | None = Form(None),
    editor_user_ids: list[int] | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page_or_404(session, page_id)
    require_page_edit(session, page, current_user)
    is_owner = page.author_id == current_user.id

    cleaned_title = title.strip()
    if not cleaned_title:
        raise HTTPException(status_code=422, detail="O título é obrigatório")

    updates: dict = {
        "title": cleaned_title,
        "summary": summary.strip(),
        "page_type": page_type,
        "status": status,
    }
    if is_owner:
        if visibility is not None:
            updates["visibility"] = visibility
        if visibility == PageVisibility.PRIVATE:
            updates["edit_policy"] = EditPolicy.OWNER
        elif editor_user_ids and edit_policy == EditPolicy.OWNER:
            updates["edit_policy"] = EditPolicy.CUSTOM
        elif edit_policy is not None:
            updates["edit_policy"] = edit_policy
        if folder_id is not None:
            parsed_folder_id = _parse_folder_id(folder_id)
            if parsed_folder_id is not None:
                folder = session.get(Folder, parsed_folder_id)
                if folder is None:
                    raise HTTPException(status_code=404, detail="Pasta não encontrada")
                require_folder_edit(folder, current_user)
            updates["folder_id"] = parsed_folder_id

    page = update_page(session, page, PageUpdate(**updates))
    if is_owner:
        replace_page_shares(
            session,
            page,
            current_user.id,
            shared_user_ids or [],
            editor_user_ids or [],
        )
        session.commit()

    return templates.TemplateResponse(
        request=request,
        name="partials/page_response.html",
        context={
            "page": page,
            "blocks": _blocks(session, page.id),
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
            "owned_folders": _owned_folders(session, current_user) if is_owner else [],
        },
    )


@router.delete("/{page_id}", response_class=HTMLResponse)
def remove_page(
    request: Request,
    page_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = _page_or_404(session, page_id)
    require_page_owner(page, current_user)
    delete_page(session, page)
    if not request.headers.get("HX-Request"):
        return Response(status_code=204)
    return templates.TemplateResponse(
        request=request,
        name="partials/page_deleted.html",
        context=_sidebar_context(session, current_user),
    )
