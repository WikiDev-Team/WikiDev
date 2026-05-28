from fastapi.responses import HTMLResponse
from fastapi import APIRouter, Depends, HTTPException, Query, Form
#from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..db import get_session
from ..models import Page, PageCreate, PageRead, PageUpdate
from ..crud import create_page, update_page

router = APIRouter(prefix="/pages", tags=["pages"])


@router.get("/", response_model=list[PageRead])
def list_pages(
    session: Session = Depends(get_session),
    language_id: int | None = None,
    page_type: str | None = None,
    status: str | None = None,
    q: str | None = None,
):
    stmt = select(Page).order_by(Page.created_at.desc())

    if language_id is not None:
        stmt = stmt.where(Page.language_id == language_id)
    if page_type is not None:
        stmt = stmt.where(Page.page_type == page_type)
    if status is not None:
        stmt = stmt.where(Page.status == status)
    if q:
        stmt = stmt.where(Page.title.ilike(f"%{q}%"))

    return session.exec(stmt).unique().all()


@router.post("/", response_model=PageRead, status_code=201)
def add_page(payload: PageCreate, session: Session = Depends(get_session)):
    return create_page(session, payload)

@router.post("/htmx", response_class=HTMLResponse)
def add_page_htmx(
    title: str = Form(...),
    summary: str = Form(""),
    content: str = Form(""),
    page_type: str = Form("personal"),
    status: str = Form("draft"),
    tag_ids: str = Form(""),
    session: Session = Depends(get_session),
):
    parsed_tag_ids = [
        int(tag_id.strip())
        for tag_id in tag_ids.split(",")
        if tag_id.strip()
    ]

    payload = PageCreate(
        title=title,
        summary=summary,
        content=content,
        page_type=page_type,
        status=status,
        tag_ids=parsed_tag_ids,
    )

    page = create_page(session, payload)

    return f"""
    <li>
        <div class="folder-item">
            {page.title}
        </div>
    </li>
    """


@router.get("/{page_id}", response_model=PageRead)
def get_page(page_id: int, session: Session = Depends(get_session)):
    stmt = select(Page).where(Page.id == page_id)
    obj = session.exec(stmt).unique().first()
    if obj is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return obj


@router.patch("/{page_id}", response_model=PageRead)
def edit_page(page_id: int, payload: PageUpdate, session: Session = Depends(get_session)):
    obj = session.get(Page, page_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    return update_page(session, obj, payload)


@router.delete("/{page_id}", status_code=204)
def remove_page(page_id: int, session: Session = Depends(get_session)):
    obj = session.get(Page, page_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    session.delete(obj)
    session.commit()
