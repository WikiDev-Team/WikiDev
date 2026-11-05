import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlmodel import Session, select

from ..collab import HEARTBEAT_SECONDS, merge3, presence
from ..crud import create_page, create_page_block, delete_page_block, update_page_block
from ..db import get_session
from ..dependencies import get_current_user
from ..models import (
    Comment,
    Page,
    PageBlock,
    PageBlockCreate,
    PageBlockType,
    PageBlockUpdate,
    PageCreate,
    PageRevision,
    PageStatus,
    PageType,
    PageVisibility,
    User,
)
from ..permissions import can_edit_page, list_accessible_pages, require_page_edit, require_page_view
from ..revisions import ensure_baseline, record_revision
from ..run_output import RunOutputError, RunOutputPayload, serialize_run_output
from ..navigation import page_nav_context, record_page_view
from ..templates import templates
from ..wiki import backlinks, wiki_index

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


def block_comment_counts(session: Session, blocks: list[PageBlock]) -> dict[int, int]:
    block_ids = [block.id for block in blocks]
    if not block_ids:
        return {}
    comments = session.exec(
        select(Comment).where(Comment.block_id.in_(block_ids), Comment.is_deleted.is_(False))
    ).all()
    counts = {block_id: 0 for block_id in block_ids}
    for comment in comments:
        counts[comment.block_id] += 1
    return counts


def wiki_index_for(session: Session, current_user: User) -> dict[str, int]:
    return wiki_index(list_accessible_pages(session, current_user.id), current_user)


def page_view_context(session: Session, page: Page, current_user: User) -> dict:
    blocks = list_blocks(session, page.id)
    return {
        "heartbeat_seconds": HEARTBEAT_SECONDS,
        "wiki_index": wiki_index_for(session, current_user),
        "backlinks": backlinks(session, page, current_user),
        "page": page,
        "blocks": blocks,
        "block_comment_counts": block_comment_counts(session, blocks),
        "can_edit": can_edit_page(session, page, current_user),
        "is_owner": page.author_id == current_user.id,
        **page_nav_context(session, page, current_user),
    }


@router.get("/{page_id}/blocks-editor", response_class=HTMLResponse)
def blocks_editor(
    request: Request,
    page_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = get_page_or_404(session, page_id)
    require_page_view(session, page, current_user)
    record_page_view(session, current_user.id, page.id)
    return templates.TemplateResponse(
        request=request,
        name="partials/page_blocks_editor.html",
        context=page_view_context(session, page, current_user),
    )


@router.post("/{page_id}/blocks", response_class=HTMLResponse)
def add_block(
    request: Request,
    page_id: int,
    block_type: PageBlockType = Form(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    page = get_page_or_404(session, page_id)
    require_page_edit(session, page, current_user)

    payload = PageBlockCreate(
        block_type=block_type,
        content="",
        language="python" if block_type == PageBlockType.CODE else "",
        font_size="normal",
    )
    ensure_baseline(session, page)
    block = create_page_block(session, page_id, payload)
    record_revision(session, page, current_user)

    return templates.TemplateResponse(
        request=request,
        name="partials/page_block_form.html",
        context={"block": block, "can_edit": True},
    )


@router.get("/blocks/{block_id}", response_class=HTMLResponse)
def get_block_partial(
    request: Request,
    block_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    block = get_block_or_404(session, block_id)
    page = get_page_or_404(session, block.page_id)
    require_page_view(session, page, current_user)

    return templates.TemplateResponse(
        request=request,
        name="partials/page_block.html",
        context={
            "block": block,
            "can_edit": can_edit_page(session, page, current_user),
            "block_comment_counts": block_comment_counts(session, [block]),
            "wiki_index": wiki_index_for(session, current_user),
        },
    )


@router.get("/blocks/{block_id}/edit", response_class=HTMLResponse)
def edit_block_form(
    request: Request,
    block_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    block = get_block_or_404(session, block_id)
    page = get_page_or_404(session, block.page_id)
    require_page_edit(session, page, current_user)
    presence.start_editing(page.id, current_user, block.id)

    return templates.TemplateResponse(
        request=request,
        name="partials/page_block_form.html",
        context={
            "block": block,
            "can_edit": True,
            "block_comment_counts": block_comment_counts(session, [block]),
            "co_editors": presence.editing_block(page.id, block.id, current_user.id),
        },
    )


def last_editor_name(session: Session, page: Page, exclude_user_id: int) -> str:
    """Quem salvou por último a página (para dizer com quem mesclamos)."""
    revision = session.exec(
        select(PageRevision)
        .where(PageRevision.page_id == page.id, PageRevision.author_id != exclude_user_id)
        .order_by(PageRevision.updated_at.desc(), PageRevision.id.desc())
    ).first()
    author = session.get(User, revision.author_id) if revision and revision.author_id else None
    if author is None:
        return "outra pessoa"
    return author.display_name or author.username


@router.patch("/blocks/{block_id}", response_class=HTMLResponse)
def update_block(
    request: Request,
    block_id: int,
    content: str = Form(""),
    language: str = Form(""),
    font_size: str = Form("normal"),
    base_content: str | None = Form(None),
    base_version: str | None = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    block = session.get(PageBlock, block_id)
    if block is None:
        if base_version is not None:
            # Outra pessoa excluiu o bloco enquanto este formulário estava aberto:
            # devolve o texto para não perder o que foi escrito.
            return templates.TemplateResponse(
                request=request,
                name="partials/page_block_gone.html",
                context={"block_id": block_id, "content": content},
            )
        raise HTTPException(status_code=404, detail="Bloco não encontrado")
    page = get_page_or_404(session, block.page_id)
    require_page_edit(session, page, current_user)

    note = ""
    merge_notice = ""
    changed_meanwhile = (
        base_version is not None
        and base_content is not None
        and block.updated_at.isoformat() != base_version
        and (block.content or "") != base_content
    )
    if changed_meanwhile and content != (block.content or ""):
        other = last_editor_name(session, page, current_user.id)
        result = merge3(base_content, content, block.content or "", theirs_name=other)
        if not result.clean:
            # Conflito: nada é salvo; a pessoa vê as duas versões e decide.
            return templates.TemplateResponse(
                request=request,
                name="partials/page_block_form.html",
                context={
                    "block": block,
                    "can_edit": True,
                    "draft": result.content,
                    "draft_language": language,
                    "draft_font_size": font_size,
                    "conflict_with": other,
                    "conflict_count": result.conflicts,
                    "block_comment_counts": block_comment_counts(session, [block]),
                },
            )
        content = result.content
        note = f"Mesclada com a edição simultânea de {other}"
        merge_notice = f"Suas alterações foram combinadas com as de {other}."

    if block.block_type == PageBlockType.TEXT:
        payload = PageBlockUpdate(content=content, language="", font_size=font_size)
    else:
        payload = PageBlockUpdate(content=content, language=language)

    if block.block_type == PageBlockType.CODE and (
        block.content != content or (block.language or "") != language
    ):
        # A saída salva mostrava outro código; não pode continuar parecendo atual.
        block.run_output = None

    ensure_baseline(session, page)
    block = update_page_block(session, block, payload)
    record_revision(session, page, current_user, note=note)
    return templates.TemplateResponse(
        request=request,
        name="partials/page_block.html",
        context={
            "block": block,
            "can_edit": True,
            "merge_notice": merge_notice,
            "block_comment_counts": block_comment_counts(session, [block]),
            "wiki_index": wiki_index_for(session, current_user),
        },
    )


def _parse_ids(raw: str) -> set[int]:
    return {int(item) for item in raw.split(",") if item.strip().isdigit()}


def _parse_known(raw: str) -> dict[int, str]:
    """``"12=2026-11-05T13:00:00.123,13=..."`` → {12: "2026-...", 13: ...}."""
    known: dict[int, str] = {}
    for item in raw.split(","):
        block_id, _, version = item.strip().partition("=")
        if block_id.isdigit():
            known[int(block_id)] = version
    return known


@router.post("/{page_id}/presence", response_class=HTMLResponse)
def page_presence(
    request: Request,
    page_id: int,
    editing: str = Form(""),
    known: str = Form(""),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Sinal periódico de quem está na página; devolve também o que mudou.

    A aba informa a versão (``updated_at``) de cada bloco que tem na tela; os
    blocos com versão diferente, novos ou excluídos voltam como hx-swap-oob.
    """
    page = get_page_or_404(session, page_id)
    require_page_view(session, page, current_user)

    editing_ids = _parse_ids(editing)
    known_versions = _parse_known(known)
    presence.touch(page.id, current_user, editing_ids)

    blocks = list_blocks(session, page.id)
    current_ids = {block.id for block in blocks}
    changed = [
        block for block in blocks
        if block.id in known_versions
        and block.id not in editing_ids
        and known_versions[block.id] != block.updated_at.isoformat()
    ]
    added = [block for block in blocks if block.id not in known_versions]
    removed = sorted(set(known_versions) - current_ids - editing_ids)
    others = presence.others(page.id, current_user.id)
    busy = {}
    for person in others:
        for block_id in person.editing:
            if block_id in current_ids:
                busy.setdefault(str(block_id), []).append(person.name)

    return templates.TemplateResponse(
        request=request,
        name="partials/page_presence.html",
        context={
            "page": page,
            "others": others,
            "busy_json": json.dumps(busy, ensure_ascii=False),
            "changed": changed,
            "added": added,
            "removed": removed,
            "can_edit": can_edit_page(session, page, current_user),
            "block_comment_counts": block_comment_counts(session, changed + added),
            "wiki_index": wiki_index_for(session, current_user) if changed or added else {},
        },
    )


@router.delete("/blocks/{block_id}", response_class=HTMLResponse)
def remove_block(
    block_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    block = get_block_or_404(session, block_id)
    page = get_page_or_404(session, block.page_id)
    require_page_edit(session, page, current_user)
    ensure_baseline(session, page)
    delete_page_block(session, block)
    record_revision(session, page, current_user)
    return HTMLResponse("")


# ── Python executável ────────────────────────────────────────────────────────


def get_python_block_or_404(session: Session, block_id: int) -> PageBlock:
    block = get_block_or_404(session, block_id)
    if block.block_type != PageBlockType.CODE or block.language != "python":
        raise HTTPException(status_code=400, detail="Só blocos de Python podem guardar saída")
    return block


@router.put("/blocks/{block_id}/output", status_code=204)
def save_block_output(
    block_id: int,
    payload: RunOutputPayload,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Guarda a saída da última execução para quem abrir a página ver sem rodar."""
    block = get_python_block_or_404(session, block_id)
    page = get_page_or_404(session, block.page_id)
    require_page_edit(session, page, current_user)
    try:
        block.run_output = serialize_run_output(payload)
    except RunOutputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    session.add(block)
    session.commit()
    return Response(status_code=204)


@router.delete("/blocks/{block_id}/output", status_code=204)
def clear_block_output(
    block_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    block = get_python_block_or_404(session, block_id)
    page = get_page_or_404(session, block.page_id)
    require_page_edit(session, page, current_user)
    block.run_output = None
    session.add(block)
    session.commit()
    return Response(status_code=204)


def _markdown_link_text(text: str) -> str:
    return "".join(f"\\{char}" if char in "\\[]*_`<>" else char for char in text)


@router.post("/blocks/{block_id}/fork")
def fork_code_block(
    block_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Cria uma página privada de quem clicou com uma cópia editável do bloco."""
    block = get_block_or_404(session, block_id)
    if block.block_type != PageBlockType.CODE:
        raise HTTPException(status_code=400, detail="Só blocos de código podem ser bifurcados")
    page = get_page_or_404(session, block.page_id)
    require_page_view(session, page, current_user)

    title = f"Cópia de {page.title}"[:200]
    new_page = create_page(
        session,
        PageCreate(
            title=title,
            page_type=PageType.PERSONAL,
            status=PageStatus.DRAFT,
            visibility=PageVisibility.PRIVATE,
            author_id=current_user.id,
            summary=f"Bifurcado de “{page.title}”"[:500],
        ),
    )
    create_page_block(
        session,
        new_page.id,
        PageBlockCreate(
            block_type=PageBlockType.TEXT,
            content=f"Código copiado de [{_markdown_link_text(page.title)}](/p/{page.id}). Edite à vontade: esta página é só sua.",
        ),
    )
    copy = create_page_block(
        session,
        new_page.id,
        PageBlockCreate(block_type=PageBlockType.CODE, content=block.content, language=block.language),
    )
    if block.run_output:
        copy.run_output = block.run_output
        session.add(copy)
        session.commit()
    return Response(status_code=200, headers={"HX-Redirect": f"/p/{new_page.id}"})
