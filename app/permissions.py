from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session, select

from .models import Folder, FolderVisibility, Page, PageStatus, User


def can_view_folder(session: Session, folder: Folder, current_user: User) -> bool:
    if folder.author_id == current_user.id:
        return True
    if folder.visibility != FolderVisibility.PUBLIC:
        return False

    # A public child must not bypass a private ancestor.
    visited = {folder.id}
    parent_id = folder.parent_folder_id
    while parent_id is not None:
        if parent_id in visited:
            return False
        visited.add(parent_id)
        parent = session.get(Folder, parent_id)
        if parent is None:
            return False
        if parent.author_id != current_user.id and parent.visibility != FolderVisibility.PUBLIC:
            return False
        parent_id = parent.parent_folder_id
    return True


def can_edit_folder(folder: Folder, current_user: User) -> bool:
    return folder.author_id == current_user.id


def can_view_page(session: Session, page: Page, current_user: User) -> bool:
    if page.author_id == current_user.id:
        return True
    if page.status != PageStatus.PUBLISHED:
        return False
    if page.folder_id is None:
        return True
    folder = session.get(Folder, page.folder_id)
    return folder is not None and can_view_folder(session, folder, current_user)


def can_edit_page(page: Page, current_user: User) -> bool:
    return page.author_id == current_user.id


def require_folder_view(session: Session, folder: Folder, current_user: User) -> None:
    if not can_view_folder(session, folder, current_user):
        raise HTTPException(status_code=403, detail="Você não pode acessar esta pasta")


def require_folder_edit(folder: Folder, current_user: User) -> None:
    if not can_edit_folder(folder, current_user):
        raise HTTPException(status_code=403, detail="Você não pode alterar esta pasta")


def require_page_view(session: Session, page: Page, current_user: User) -> None:
    if not can_view_page(session, page, current_user):
        raise HTTPException(status_code=403, detail="Você não pode acessar esta página")


def require_page_edit(page: Page, current_user: User) -> None:
    if not can_edit_page(page, current_user):
        raise HTTPException(status_code=403, detail="Você não pode alterar esta página")


def accessible_pages(session: Session, current_user: User) -> list[Page]:
    pages = session.exec(select(Page).order_by(Page.created_at.desc())).all()
    return [page for page in pages if can_view_page(session, page, current_user)]


def accessible_folders(session: Session, current_user: User) -> list[Folder]:
    folders = session.exec(select(Folder).order_by(Folder.name)).all()
    return [folder for folder in folders if can_view_folder(session, folder, current_user)]
