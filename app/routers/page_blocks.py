from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select

from ..crud import create_page_block, delete_page_block, update_page_block
from ..db import get_session
from ..models import Page, PageBlock, PageBlockCreate, PageBlockType, PageBlockUpdate
from ..templates import templates


router = APIRouter(prefix="/pages", tags=["page-blocks"])


def get_page_or_404(session: Session, page_id: int) -> Page:
    page = session.get(Page, page_id)

    if page is None:
        raise HTTPException(status_code=404, detail="Página não encontrada")

    return page


def get_block_or_404(session: Session, block_id: int) -> PageBlock:
    block = session.get(PageBlock, block_id)

    if block is None:
        raise HTTPException(status_code=404, detail="Bloco não encontrado")

    return block


def list_blocks(session: Session, page_id: int) -> list[PageBlock]:
    return session.exec(
        select(PageBlock)
        .where(PageBlock.page_id == page_id)
        .order_by(PageBlock.position.asc(), PageBlock.id.asc())
    ).all()


@router.get("/{page_id}/blocks-editor", response_class=HTMLResponse)
def blocks_editor(
    request: Request,
    page_id: int,
    session: Session = Depends(get_session),
):
    page = get_page_or_404(session, page_id)
    blocks = list_blocks(session, page_id)

    return templates.TemplateResponse(
        request=request,
        name="partials/page_blocks_editor.html",
        context={
            "page": page,
            "blocks": blocks,
        },
    )


@router.post("/{page_id}/blocks", response_class=HTMLResponse)
def add_block(
    request: Request,
    page_id: int,
    block_type: PageBlockType = Form(...),
    session: Session = Depends(get_session),
):
    get_page_or_404(session, page_id)

    payload = PageBlockCreate(
        block_type=block_type,
        content="",
        language="python" if block_type == PageBlockType.CODE else "",
        font_size="normal",
    )

    block = create_page_block(session, page_id, payload)

    return templates.TemplateResponse(
        request=request,
        name="partials/page_block_form.html",
        context={
            "block": block,
        },
    )


@router.get("/blocks/{block_id}", response_class=HTMLResponse)
def get_block_partial(
    request: Request,
    block_id: int,
    session: Session = Depends(get_session),
):
    block = get_block_or_404(session, block_id)

    return templates.TemplateResponse(
        request=request,
        name="partials/page_block.html",
        context={
            "block": block,
        },
    )


@router.get("/blocks/{block_id}/edit", response_class=HTMLResponse)
def edit_block_form(
    request: Request,
    block_id: int,
    session: Session = Depends(get_session),
):
    block = get_block_or_404(session, block_id)

    return templates.TemplateResponse(
        request=request,
        name="partials/page_block_form.html",
        context={
            "block": block,
        },
    )


@router.patch("/blocks/{block_id}", response_class=HTMLResponse)
def update_block(
    request: Request,
    block_id: int,
    content: str = Form(""),
    language: str = Form(""),
    font_size: str = Form("normal"),
    session: Session = Depends(get_session),
):
    block = get_block_or_404(session, block_id)

    if block.block_type == PageBlockType.TEXT:
        payload = PageBlockUpdate(
            content=content,
            language="",
            font_size=font_size,
        )
        
    else:
        payload = PageBlockUpdate(
            content=content,
            language=language,
        )

    block = update_page_block(session, block, payload)

    return templates.TemplateResponse(
        request=request,
        name="partials/page_block.html",
        context={
            "block": block,
        },
    )


@router.delete("/blocks/{block_id}", response_class=HTMLResponse)
def remove_block(
    block_id: int,
    session: Session = Depends(get_session),
):
    block = get_block_or_404(session, block_id)

    delete_page_block(session, block)

    return HTMLResponse("")