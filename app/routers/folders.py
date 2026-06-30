from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Folder, FolderCreate, FolderRead, FolderUpdate, Page, PageRead
from ..crud import create_folder, update_folder

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("/", response_model=list[FolderRead])
def list_folders(
    session: Session = Depends(get_session),
    author_id: int | None = None,
    parent_folder_id: int | None = None,
    q: str | None = None,
):
    """Lista todas as pastas com filtros opcionais."""
    stmt = select(Folder).order_by(Folder.name)
    if author_id is not None:
        stmt = stmt.where(Folder.author_id == author_id)
    if parent_folder_id is not None:
        stmt = stmt.where(Folder.parent_folder_id == parent_folder_id)
    if q:
        stmt = stmt.where(Folder.name.ilike(f"%{q}%"))
    return session.exec(stmt).all()


@router.post("/", response_model=FolderRead, status_code=201)
def add_folder(payload: FolderCreate, session: Session = Depends(get_session)):
    """Cria uma nova pasta."""
    return create_folder(session, payload)


@router.get("/{folder_id}", response_model=FolderRead)
def get_folder(folder_id: int, session: Session = Depends(get_session)):
    """Retorna uma pasta pelo ID."""
    obj = session.get(Folder, folder_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Pasta não encontrada")
    return obj


@router.get("/{folder_id}/pages", response_model=list[PageRead])
def list_folder_pages(
    folder_id: int,
    session: Session = Depends(get_session),
    status: str | None = None,
):
    """Lista todas as páginas de uma pasta."""
    if session.get(Folder, folder_id) is None:
        raise HTTPException(status_code=404, detail="Pasta não encontrada")
    stmt = select(Page).where(Page.folder_id == folder_id).order_by(Page.created_at.desc())
    if status is not None:
        stmt = stmt.where(Page.status == status)
    return session.exec(stmt).unique().all()


@router.patch("/{folder_id}", response_model=FolderRead)
def edit_folder(folder_id: int, payload: FolderUpdate, session: Session = Depends(get_session)):
    """Edita uma pasta existente."""
    obj = session.get(Folder, folder_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Pasta não encontrada")
    return update_folder(session, obj, payload)


@router.delete("/{folder_id}", status_code=204)
def remove_folder(folder_id: int, session: Session = Depends(get_session)):
    """Deleta uma pasta (páginas dentro dela ficam sem pasta associada)."""
    obj = session.get(Folder, folder_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Pasta não encontrada")
    for page in session.exec(select(Page).where(Page.folder_id == folder_id)).all():
        page.folder_id = None
        session.add(page)
    for subfolder in session.exec(select(Folder).where(Folder.parent_folder_id == folder_id)).all():
        subfolder.parent_folder_id = None
        session.add(subfolder)
    session.delete(obj)
    session.commit()
