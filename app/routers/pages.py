from fastapi.responses import HTMLResponse
from fastapi import APIRouter, Depends, HTTPException, Query, Form, Request
#from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..db import get_session
from ..models import Page, PageCreate, PageRead, PageUpdate, User, PageTagLink, PageBlock
from ..crud import create_page, update_page
from ..dependencies import get_current_user
from ..templates import templates

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

# JSON
# @router.post("/", response_model=PageRead, status_code=201)
# def add_page(payload: PageCreate, session: Session = Depends(get_session)):
#     return create_page(session, payload)

@router.post("/", response_class=HTMLResponse)
def add_page_htmx(
    request: Request,
    title: str = Form(...),
    summary: str = Form(""),
    page_type: str = Form("note"),
    status: str = Form("draft"),
    tag_ids: str = Form(""),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    parsed_tag_ids = [
        int(tag_id.strip())
        for tag_id in tag_ids.split(",")
        if tag_id.strip()
    ]

    payload = PageCreate(
        title=title,
        summary=summary,
        page_type=page_type,
        status=status,
        author_id=current_user.id,
        tag_ids=parsed_tag_ids,
    )

    page = create_page(session, payload)

    pages = session.exec(
        select(Page).order_by(Page.created_at.desc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="partials/page_response.html",
        context={
            "page": page,
            "pages": pages,
            "blocks": [],
        },
    )

#JSON
# @router.get("/{page_id}", response_model=PageRead)
# def get_page(page_id: int, session: Session = Depends(get_session)):
#     stmt = select(Page).where(Page.id == page_id)
#     obj = session.exec(stmt).unique().first()
#     if obj is None:
#         raise HTTPException(status_code=404, detail="Página não encontrada")
#     return obj

#JSON
# @router.patch("/{page_id}", response_model=PageRead)
# def edit_page(page_id: int, payload: PageUpdate, session: Session = Depends(get_session)):
#   obj = session.get(Page, page_id)
#       if obj is None:
#       raise HTTPException(status_code=404, detail="Página não encontrada")
#   return update_page(session, obj, payload)


@router.delete("/{page_id}", status_code=204)
def remove_page(page_id: int, session: Session = Depends(get_session)):
    """Deleta uma página."""
    obj = session.get(Page, page_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")
    session.delete(obj)
    session.commit()

@router.get("/new", response_class=HTMLResponse)
def new_page_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="partials/page_create.html",
        context={},
    )


# Removemos quando mudamos para blocks
#@router.get("/{page_id}", response_class=HTMLResponse)
#def get_page(
#    request: Request,
#    page_id: int,
#    session: Session = Depends(get_session),
#):
#    page = session.get(Page, page_id)
#
#    if page is None:
#        raise HTTPException(status_code=404, detail="Página não encontrada")
#
#    return templates.TemplateResponse(
#        request=request,
#        name="partials/page_editor.html",
#        context={"page": page},
#    )
#

@router.patch("/{page_id}", response_class=HTMLResponse)
def edit_page(
    request: Request,
    page_id: int,
    title: str = Form(...),
    summary: str = Form(""),
    page_type: str = Form("note"),
    status: str = Form("draft"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = session.get(Page, page_id)

    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")

    if page.author_id is None:
        page.author_id = current_user.id

    payload = PageUpdate(
        title=title,
        summary=summary,
        page_type=page_type,
        status=status,
    )

    page = update_page(session, page, payload)

    blocks = session.exec(
        select(PageBlock)
        .where(PageBlock.page_id == page.id)
        .order_by(PageBlock.position.asc(), PageBlock.id.asc())
    ).all()

    pages = session.exec(
        select(Page).order_by(Page.created_at.desc())
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="partials/page_response.html",
        context={
            "page": page,
            "pages": pages,
            "blocks": blocks,
        },
    )

@router.get("/{page_id}/metadata/edit", response_class=HTMLResponse)
def edit_page_metadata_form(
    request: Request,
    page_id: int,
    session: Session = Depends(get_session),
):
    page = session.get(Page, page_id)

    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")

    return templates.TemplateResponse(
        request=request,
        name="partials/page_metadata_form.html",
        context={
            "page": page,
        },
    )
