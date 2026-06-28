from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Page, PageCreate, PageRead, PageUpdate, PageTagLink
from ..crud import create_page, update_page

router = APIRouter(prefix="/pages", tags=["pages"])


@router.get("/", response_model=list[PageRead])
def list_pages(
    session: Session = Depends(get_session),
    language_id: int | None = None,
    page_type: str | None = None,
    status: str | None = None,
    folder_id: int | None = None,
    tag_id: int | None = None,
    q: str | None = None,
):
    """Lista páginas com filtros opcionais por linguagem, tipo, status, pasta, tag e busca."""
    stmt = select(Page).order_by(Page.created_at.desc())
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


@router.post("/", response_model=PageRead, status_code=201)
def add_page(payload: PageCreate, session: Session = Depends(get_session)):
    """Cria uma nova página."""
    return create_page(session, payload)


@router.get("/{page_id}", response_model=PageRead)
def get_page(page_id: int, session: Session = Depends(get_session)):
    """Retorna uma página pelo ID."""
    obj = session.exec(select(Page).where(Page.id == page_id)).unique().first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return obj


@router.patch("/{page_id}", response_model=PageRead)
def edit_page(page_id: int, payload: PageUpdate, session: Session = Depends(get_session)):
    """Edita uma página existente."""
    obj = session.get(Page, page_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return update_page(session, obj, payload)


@router.delete("/{page_id}", status_code=204)
def remove_page(page_id: int, session: Session = Depends(get_session)):
    """Deleta uma página."""
    obj = session.get(Page, page_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    session.delete(obj)
    session.commit()
