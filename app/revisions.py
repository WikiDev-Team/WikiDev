"""Histórico de versões das páginas.

Cada alteração de conteúdo grava uma foto da página (título, resumo e blocos).
Edições seguidas da mesma pessoa em poucos minutos são agrupadas numa só
versão, para o histórico não virar uma lista de cada tecla salva.
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlmodel import Session, select

from .crud import create_page_block, delete_page_block, update_page
from .models import (
    Page,
    PageBlock,
    PageBlockCreate,
    PageBlockType,
    PageRevision,
    PageUpdate,
    User,
    now_utc,
)

COALESCE_WINDOW = timedelta(minutes=5)
BASELINE_NOTE = "Versão inicial"


def _blocks(session: Session, page_id: int) -> list[PageBlock]:
    return session.exec(
        select(PageBlock)
        .where(PageBlock.page_id == page_id)
        .order_by(PageBlock.position.asc(), PageBlock.id.asc())
    ).all()


def snapshot_blocks(session: Session, page: Page) -> list[dict]:
    return [
        {
            "id": block.id,
            "block_type": block.block_type.value,
            "content": block.content or "",
            "language": block.language or "",
            "font_size": block.font_size or "normal",
            "position": block.position,
        }
        for block in _blocks(session, page.id)
    ]


def list_revisions(session: Session, page_id: int) -> list[PageRevision]:
    return session.exec(
        select(PageRevision)
        .where(PageRevision.page_id == page_id)
        .order_by(PageRevision.created_at.desc(), PageRevision.id.desc())
    ).all()


def _latest(session: Session, page_id: int) -> PageRevision | None:
    revisions = list_revisions(session, page_id)
    return revisions[0] if revisions else None


def ensure_baseline(session: Session, page: Page) -> None:
    """Antes da primeira edição registrada, guarda como a página estava."""
    if _latest(session, page.id) is not None:
        return
    session.add(
        PageRevision(
            page_id=page.id,
            author_id=page.author_id,
            title=page.title,
            summary=page.summary or "",
            snapshot=json.dumps(snapshot_blocks(session, page), ensure_ascii=False),
            note=BASELINE_NOTE,
            created_at=page.updated_at or page.created_at,
            updated_at=page.updated_at or page.created_at,
        )
    )
    session.commit()


def record_revision(session: Session, page: Page, user: User, note: str = "") -> PageRevision:
    """Grava o estado atual da página como uma versão (ou atualiza a última)."""
    now = now_utc()
    snapshot = json.dumps(snapshot_blocks(session, page), ensure_ascii=False)
    latest = _latest(session, page.id)

    if (
        latest is not None
        and not note
        and not latest.note
        and latest.author_id == user.id
        and now - latest.updated_at <= COALESCE_WINDOW
    ):
        revision = latest
    else:
        revision = PageRevision(page_id=page.id, author_id=user.id, note=note, created_at=now)

    revision.title = page.title
    revision.summary = page.summary or ""
    revision.snapshot = snapshot
    revision.updated_at = now
    session.add(revision)

    page.updated_at = now
    session.add(page)
    session.commit()
    session.refresh(revision)
    return revision


def previous_revision(session: Session, revision: PageRevision) -> PageRevision | None:
    revisions = list_revisions(session, revision.page_id)
    for index, item in enumerate(revisions):
        if item.id == revision.id:
            return revisions[index + 1] if index + 1 < len(revisions) else None
    return None


# ── Diff ─────────────────────────────────────────────────────────────────────


@dataclass
class DiffLine:
    kind: str  # "add", "remove" ou "same"
    text: str


@dataclass
class BlockDiff:
    status: str  # "added", "removed", "changed" ou "same"
    block_type: str
    language: str
    lines: list[DiffLine] = field(default_factory=list)


@dataclass
class RevisionDiff:
    title_before: str | None
    title_after: str
    summary_before: str | None
    summary_after: str
    blocks: list[BlockDiff]
    added: int = 0
    removed: int = 0

    @property
    def has_changes(self) -> bool:
        return (
            self.title_before is not None
            or self.summary_before is not None
            or any(block.status != "same" for block in self.blocks)
        )


def _line_diff(before: str, after: str) -> list[DiffLine]:
    lines: list[DiffLine] = []
    for line in difflib.ndiff(before.splitlines(), after.splitlines()):
        tag, text = line[:2], line[2:]
        if tag == "+ ":
            lines.append(DiffLine("add", text))
        elif tag == "- ":
            lines.append(DiffLine("remove", text))
        elif tag == "  ":
            lines.append(DiffLine("same", text))
    return lines


def diff_revisions(old: PageRevision | None, new: PageRevision) -> RevisionDiff:
    old_blocks = json.loads(old.snapshot) if old else []
    new_blocks = json.loads(new.snapshot)
    old_by_id = {block["id"]: block for block in old_blocks}
    new_ids = {block["id"] for block in new_blocks}

    blocks: list[BlockDiff] = []
    for block in new_blocks:
        before = old_by_id.get(block["id"])
        if old is None:
            # Ponto de partida do histórico: mostra o conteúdo sem marcar como novo.
            lines = [DiffLine("same", text) for text in block["content"].splitlines()]
            blocks.append(BlockDiff("same", block["block_type"], block["language"], lines))
        elif before is None:
            lines = [DiffLine("add", text) for text in block["content"].splitlines()]
            blocks.append(BlockDiff("added", block["block_type"], block["language"], lines))
        elif before["content"] != block["content"] or before["language"] != block["language"]:
            lines = _line_diff(before["content"], block["content"])
            blocks.append(BlockDiff("changed", block["block_type"], block["language"], lines))
        else:
            lines = [DiffLine("same", text) for text in block["content"].splitlines()]
            blocks.append(BlockDiff("same", block["block_type"], block["language"], lines))
    for block in old_blocks:
        if block["id"] not in new_ids:
            lines = [DiffLine("remove", text) for text in block["content"].splitlines()]
            blocks.append(BlockDiff("removed", block["block_type"], block["language"], lines))

    result = RevisionDiff(
        title_before=old.title if old and old.title != new.title else None,
        title_after=new.title,
        summary_before=old.summary if old and old.summary != new.summary else None,
        summary_after=new.summary,
        blocks=blocks,
    )
    for block in blocks:
        result.added += sum(1 for line in block.lines if line.kind == "add")
        result.removed += sum(1 for line in block.lines if line.kind == "remove")
    return result


# ── Restauração ──────────────────────────────────────────────────────────────


def restore_revision(session: Session, page: Page, revision: PageRevision, user: User) -> None:
    """Volta título, resumo e blocos para o estado da versão escolhida.

    Blocos que ainda existem são atualizados no lugar (mantendo comentários);
    blocos apagados desde então são recriados; blocos que não existiam na
    versão são removidos.
    """
    ensure_baseline(session, page)
    wanted = json.loads(revision.snapshot)
    current = {block.id: block for block in _blocks(session, page.id)}
    wanted_ids = {item["id"] for item in wanted}

    for block_id, block in current.items():
        if block_id not in wanted_ids:
            delete_page_block(session, block)

    for item in wanted:
        block = current.get(item["id"])
        if block is None:
            create_page_block(
                session,
                page.id,
                PageBlockCreate(
                    block_type=PageBlockType(item["block_type"]),
                    content=item["content"],
                    language=item["language"],
                    font_size=item["font_size"],
                    position=item["position"],
                ),
            )
            continue
        block.content = item["content"]
        block.language = item["language"]
        block.font_size = item["font_size"]
        block.position = item["position"]
        block.updated_at = now_utc()
        session.add(block)

    session.commit()
    page = update_page(
        session, page, PageUpdate(title=revision.title or page.title, summary=revision.summary)
    )
    stamp = revision.created_at.strftime("%d/%m/%Y %H:%M") if isinstance(revision.created_at, datetime) else ""
    record_revision(session, page, user, note=f"Restaurada a versão de {stamp}".strip())
