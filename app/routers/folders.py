from __future__ import annotations
from sqlalchemy import delete
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select
from typing import Annotated
from ..crud import create_folder, create_page, update_folder
from ..db import get_session
from ..dependencies import get_current_user
from ..models import (
    EditPolicy,
    Folder,
    FolderShare,
    FolderCreate,
    FolderRead,
    FolderUpdate,
    FolderVisibility,
    Page,
    PageCreate,
    PageRead,
    PageVisibility,
    User,
)
from ..permissions import (
    accessible_folders,
    can_edit_folder,
    can_manage_folder,
    can_view_folder,
    can_view_page,
    get_folder_share_user_ids,
    get_friend_users,
    replace_folder_shares,
    require_folder_edit,
    require_folder_owner,
    require_folder_view,
    require_page_view,
)

from ..templates import templates

router = APIRouter(prefix="/folders", tags=["folders"])


def _folder_or_404(session: Session, folder_id: int) -> Folder:
    folder = session.get(Folder, folder_id)
    if folder is None:
        raise HTTPException(status_code=404, detail="Pasta não encontrada")
    return folder


def _page_or_404(session: Session, page_id: int) -> Page:
    page = session.get(Page, page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return page


def _clean_folder_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise HTTPException(status_code=422, detail="O nome da pasta é obrigatório")
    return name


def _parse_optional_id(value: str, *, field_name: str) -> int | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if not cleaned.isdigit():
        raise HTTPException(status_code=422, detail=f"{field_name} inválido")
    return int(cleaned)


def _validate_parent(
    session: Session,
    parent_folder_id: int | None,
    current_user: User,
    *,
    edited_folder_id: int | None = None,
) -> None:
    if parent_folder_id is None:
        return
    parent = _folder_or_404(session, parent_folder_id)
    require_folder_owner(parent, current_user)

    visited: set[int] = set()
    cursor: Folder | None = parent
    while cursor is not None:
        if cursor.id in visited:
            raise HTTPException(status_code=409, detail="A hierarquia de pastas contém um ciclo")
        if edited_folder_id is not None and cursor.id == edited_folder_id:
            raise HTTPException(status_code=422, detail="Uma pasta não pode conter a si mesma")
        visited.add(cursor.id)
        cursor = (
            session.get(Folder, cursor.parent_folder_id)
            if cursor.parent_folder_id is not None
            else None
        )


def _folder_panel_context(session: Session, folder: Folder, current_user: User) -> dict:
    folder_pages = session.exec(
        select(Page).where(Page.folder_id == folder.id).order_by(Page.created_at.desc())
    ).all()
    visible_pages = [page for page in folder_pages if can_view_page(session, page, current_user)]
    attachable_pages = session.exec(
        select(Page).where(Page.author_id == current_user.id).order_by(Page.title)
    ).all()
    attachable_pages = [page for page in attachable_pages if page.folder_id != folder.id]
    subfolders = session.exec(
        select(Folder).where(Folder.parent_folder_id == folder.id).order_by(Folder.name)
    ).all()
    subfolders = [item for item in subfolders if can_view_folder(session, item, current_user)]
    return {
        "folder": folder,
        "folder_pages": visible_pages,
        "attachable_pages": attachable_pages,
        "subfolders": subfolders,
        "can_edit": can_edit_folder(session, folder, current_user),
        "can_manage": can_manage_folder(folder, current_user),
    }


@router.get("/new", response_class=HTMLResponse)
def new_folder_form(
    request: Request,
    parent_folder_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    owned_folders = session.exec(
        select(Folder).where(Folder.author_id == current_user.id).order_by(Folder.name)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="partials/folder_form.html",
        context={
            "folder": None,
            "owned_folders": owned_folders,
            "selected_parent_id": parent_folder_id,
            "friends": get_friend_users(
                session,
                current_user.id,
            ),
            "shared_user_ids": set(),
            "editor_user_ids": set(),
        },
    )


@router.post("/ui", response_class=HTMLResponse)
def create_folder_ui(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    visibility: FolderVisibility = Form(
        FolderVisibility.PRIVATE
    ),
    edit_policy: EditPolicy = Form(EditPolicy.OWNER),
    parent_folder_id: str = Form(""),
    shared_user_ids: Annotated[
        list[int] | None,
        Form(),
    ] = None,
    editor_user_ids: Annotated[
        list[int] | None,
        Form(),
    ] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    
    parsed_parent = _parse_optional_id(parent_folder_id, field_name="Pasta pai")
    _validate_parent(session, parsed_parent, current_user)
    if visibility == FolderVisibility.PRIVATE:
        edit_policy = EditPolicy.OWNER
    elif editor_user_ids and edit_policy == EditPolicy.OWNER:
        edit_policy = EditPolicy.CUSTOM
    folder = create_folder(
        session,
        FolderCreate(
            name=_clean_folder_name(name),
            description=description.strip(),
            visibility=visibility,
            edit_policy=edit_policy,
            author_id=current_user.id,
            parent_folder_id=parsed_parent,
        ),
    )
    replace_folder_shares(
        session,
        folder,
        current_user.id,
        shared_user_ids or [],
        editor_user_ids or [],
    )
    session.commit()



    return templates.TemplateResponse(
        request=request,
        name="partials/folder_panel_with_sidebar.html",
        context={
            **_folder_panel_context(session, folder, current_user),
            "folders": accessible_folders(session, current_user),
            "usuario": current_user,
        },
    )


@router.get("/{folder_id}/panel", response_class=HTMLResponse)
def folder_panel(
    request: Request,
    folder_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    require_folder_view(session, folder, current_user)
    return templates.TemplateResponse(
        request=request,
        name="partials/folder_panel.html",
        context=_folder_panel_context(session, folder, current_user),
    )


@router.get("/{folder_id}/edit-form", response_class=HTMLResponse)
def edit_folder_form(
    request: Request,
    folder_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    require_folder_owner(folder, current_user)
    owned_folders = session.exec(
        select(Folder).where(Folder.author_id == current_user.id).order_by(Folder.name)
    ).all()
    return templates.TemplateResponse(
        request=request,
        name="partials/folder_form.html",
        context={
            "folder": folder,
            "owned_folders": [
                item
                for item in owned_folders
                if item.id != folder.id
            ],
            "selected_parent_id": folder.parent_folder_id,
            "friends": get_friend_users(
                session,
                current_user.id,
            ),
            "shared_user_ids": get_folder_share_user_ids(session, folder.id)[0],
            "editor_user_ids": get_folder_share_user_ids(session, folder.id)[1],
        },
    )


@router.patch("/{folder_id}/ui", response_class=HTMLResponse)
def update_folder_ui(
    request: Request,
    folder_id: int,
    name: str = Form(...),
    description: str = Form(""),
    visibility: FolderVisibility = Form(FolderVisibility.PRIVATE),
    edit_policy: EditPolicy = Form(EditPolicy.OWNER),
    parent_folder_id: str = Form(""),
    shared_user_ids: Annotated[list[int] | None, Form()] = None,
    editor_user_ids: Annotated[list[int] | None, Form()] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    require_folder_owner(folder, current_user)
    parsed_parent = _parse_optional_id(parent_folder_id, field_name="Pasta pai")
    _validate_parent(
        session,
        parsed_parent,
        current_user,
        edited_folder_id=folder.id,
    )
    folder = update_folder(
        session,
        folder,
        FolderUpdate(
            name=_clean_folder_name(name),
            description=description.strip(),
            visibility=visibility,
            edit_policy=(
                EditPolicy.OWNER
                if visibility == FolderVisibility.PRIVATE
                else EditPolicy.CUSTOM
                if editor_user_ids and edit_policy == EditPolicy.OWNER
                else edit_policy
            ),
            parent_folder_id=parsed_parent,
        ),
    )

    replace_folder_shares(
        session,
        folder,
        current_user.id,
        shared_user_ids or [],
        editor_user_ids or [],
    )
    session.commit() 

    return templates.TemplateResponse(
        request=request,
        name="partials/folder_panel_with_sidebar.html",
        context={
            **_folder_panel_context(session, folder, current_user),
            "folders": accessible_folders(session, current_user),
            "usuario": current_user,
        },
    )


@router.delete("/{folder_id}/ui", response_class=HTMLResponse)
def delete_folder_ui(
    request: Request,
    folder_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    require_folder_owner(folder, current_user)
    for page in session.exec(select(Page).where(Page.folder_id == folder_id)).all():
        page.folder_id = None
        session.add(page)
    for subfolder in session.exec(
        select(Folder).where(Folder.parent_folder_id == folder_id)
    ).all():
        subfolder.parent_folder_id = None
        session.add(subfolder)

    session.exec(
        delete(FolderShare).where(
            FolderShare.folder_id == folder.id
        )
    )

    session.delete(folder)
    session.commit()
    return templates.TemplateResponse(
        request=request,
        name="partials/folder_deleted.html",
        context={
            "folders": accessible_folders(session, current_user),
            "usuario": current_user,
        },
    )


@router.post("/{folder_id}/attach", response_class=HTMLResponse)
def attach_page_ui(
    request: Request,
    folder_id: int,
    page_id: int = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    page = _page_or_404(session, page_id)
    require_folder_edit(session, folder, current_user)
    require_page_view(session, page, current_user)
    page.folder_id = folder.id
    session.add(page)
    session.commit()
    session.refresh(page)
    return templates.TemplateResponse(
        request=request,
        name="partials/folder_panel.html",
        context=_folder_panel_context(session, folder, current_user),
    )


@router.post("/{folder_id}/detach", response_class=HTMLResponse)
def detach_page_ui(
    request: Request,
    folder_id: int,
    page_id: int = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    page = _page_or_404(session, page_id)
    require_folder_edit(session, folder, current_user)
    if page.folder_id != folder.id:
        raise HTTPException(status_code=409, detail="A página não está nesta pasta")
    page.folder_id = None
    session.add(page)
    session.commit()
    return templates.TemplateResponse(
        request=request,
        name="partials/folder_panel.html",
        context=_folder_panel_context(session, folder, current_user),
    )


@router.get("/", response_model=list[FolderRead])
def list_folders(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    author_id: int | None = None,
    parent_folder_id: int | None = None,
    q: str | None = None,
):
    folders = accessible_folders(session, current_user)
    if author_id is not None:
        folders = [folder for folder in folders if folder.author_id == author_id]
    if parent_folder_id is not None:
        folders = [folder for folder in folders if folder.parent_folder_id == parent_folder_id]
    if q:
        query = q.casefold()
        folders = [folder for folder in folders if query in folder.name.casefold()]
    return folders


@router.post("/", response_model=FolderRead, status_code=status.HTTP_201_CREATED)
def add_folder(
    payload: FolderCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    _validate_parent(session, payload.parent_folder_id, current_user)
    safe_payload = payload.model_copy(
        update={
            "author_id": current_user.id,
            "edit_policy": (
                EditPolicy.OWNER
                if payload.visibility == FolderVisibility.PRIVATE
                else payload.edit_policy
            ),
        }
    )
    return create_folder(session, safe_payload)


@router.get("/{folder_id}", response_model=FolderRead)
def get_folder(
    folder_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    require_folder_view(session, folder, current_user)
    return folder


@router.get("/{folder_id}/pages", response_model=list[PageRead])
def list_folder_pages(
    folder_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    page_status: str | None = None,
):
    folder = _folder_or_404(session, folder_id)
    require_folder_view(session, folder, current_user)
    pages = session.exec(
        select(Page).where(Page.folder_id == folder_id).order_by(Page.created_at.desc())
    ).all()
    pages = [page for page in pages if can_view_page(session, page, current_user)]
    if page_status is not None:
        pages = [page for page in pages if page.status.value == page_status]
    return pages


@router.post("/{folder_id}/pages", response_model=PageRead, status_code=status.HTTP_201_CREATED)
def create_page_in_folder(
    folder_id: int,
    payload: PageCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    require_folder_edit(session, folder, current_user)
    updates = {"folder_id": folder.id, "author_id": current_user.id}
    # Pela API de contexto, visibilidade omitida significa "herdar a pasta".
    # A página fica pública, mas continua bloqueada enquanto qualquer pasta
    # ancestral for privada. Isso permite publicar a pasta depois sem editar
    # cada página individualmente.
    if "visibility" not in payload.model_fields_set:
        updates["visibility"] = PageVisibility.PUBLIC
    safe_payload = payload.model_copy(update=updates)
    return create_page(session, safe_payload)


@router.put("/{folder_id}/pages/{page_id}", response_model=PageRead)
def add_existing_page_to_folder(
    folder_id: int,
    page_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    page = _page_or_404(session, page_id)
    require_folder_edit(session, folder, current_user)
    require_page_view(session, page, current_user)
    page.folder_id = folder.id
    session.add(page)
    session.commit()
    session.refresh(page)
    return page


@router.delete("/{folder_id}/pages/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_page_from_folder(
    folder_id: int,
    page_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    page = _page_or_404(session, page_id)
    require_folder_edit(session, folder, current_user)
    if page.folder_id != folder.id:
        raise HTTPException(status_code=409, detail="A página não está nesta pasta")
    page.folder_id = None
    session.add(page)
    session.commit()


@router.patch("/{folder_id}", response_model=FolderRead)
def edit_folder(
    folder_id: int,
    payload: FolderUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    require_folder_owner(folder, current_user)
    if "parent_folder_id" in payload.model_fields_set:
        _validate_parent(
            session,
            payload.parent_folder_id,
            current_user,
            edited_folder_id=folder.id,
        )
    folder = update_folder(
        session,
        folder,
        payload,
    )

    if (
        {"visibility", "edit_policy"} & payload.model_fields_set
        and folder.visibility != FolderVisibility.CUSTOM
        and folder.edit_policy != EditPolicy.CUSTOM
    ):
        replace_folder_shares(
            session,
            folder,
            current_user.id,
            [],
            [],
        )
        session.commit()

    return folder


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_folder(
    folder_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    require_folder_owner(folder, current_user)
    for page in session.exec(select(Page).where(Page.folder_id == folder_id)).all():
        page.folder_id = None
        session.add(page)
    for subfolder in session.exec(
        select(Folder).where(Folder.parent_folder_id == folder_id)
    ).all():
        subfolder.parent_folder_id = None
        session.add(subfolder)

    session.exec(
        delete(FolderShare).where(
            FolderShare.folder_id == folder.id
        )
    )

    session.delete(folder)
    session.commit()
