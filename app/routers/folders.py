from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..crud import create_folder, update_folder
from ..db import get_session
from ..dependencies import get_current_user
from ..models import Folder, FolderCreate, FolderRead, FolderUpdate, Page, PageRead, User
from ..permissions import accessible_pages_query

router = APIRouter(prefix="/folders", tags=["folders"])


def _folder_or_404(session: Session, folder_id: int) -> Folder:
    folder = session.get(Folder, folder_id)
    if folder is None:
        raise HTTPException(status_code=404, detail="Pasta não encontrada")
    return folder


def _require_owner(folder: Folder, current_user: User) -> None:
    if folder.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Você não pode alterar esta pasta")


@router.get("/", response_model=list[FolderRead])
def list_folders(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    parent_folder_id: int | None = None,
    q: str | None = None,
):
    """Lista as pastas do usuário autenticado."""
    stmt = select(Folder).where(Folder.author_id == current_user.id).order_by(Folder.name)
    if parent_folder_id is not None:
        stmt = stmt.where(Folder.parent_folder_id == parent_folder_id)
    if q:
        stmt = stmt.where(Folder.name.ilike(f"%{q}%"))
    return session.exec(stmt).all()


@router.post("/", response_model=FolderRead, status_code=201)
def add_folder(
    payload: FolderCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    safe_payload = payload.model_copy(update={"author_id": current_user.id})
    return create_folder(session, safe_payload)


@router.get("/{folder_id}", response_model=FolderRead)
def get_folder(
    folder_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    _require_owner(folder, current_user)
    return folder


@router.get("/{folder_id}/pages", response_model=list[PageRead])
def list_folder_pages(
    folder_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    status: str | None = None,
):
    folder = _folder_or_404(session, folder_id)
    _require_owner(folder, current_user)
    stmt = accessible_pages_query(session, current_user.id).where(Page.folder_id == folder_id)
    if status is not None:
        stmt = stmt.where(Page.status == status)
    return session.exec(stmt.order_by(Page.created_at.desc())).unique().all()


@router.patch("/{folder_id}", response_model=FolderRead)
def edit_folder(
    folder_id: int,
    payload: FolderUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    _require_owner(folder, current_user)
    safe_payload = payload.model_copy(update={"author_id": current_user.id})
    return update_folder(session, folder, safe_payload)


@router.delete("/{folder_id}", status_code=204)
def remove_folder(
    folder_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    folder = _folder_or_404(session, folder_id)
    _require_owner(folder, current_user)
    for page in session.exec(select(Page).where(Page.folder_id == folder_id)).all():
        page.folder_id = None
        session.add(page)
    for subfolder in session.exec(select(Folder).where(Folder.parent_folder_id == folder_id)).all():
        subfolder.parent_folder_id = None
        session.add(subfolder)
    session.delete(folder)
    session.commit()
