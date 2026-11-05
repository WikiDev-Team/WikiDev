"""Recursos de navegação da wiki: tags, links entre páginas e citações.

Tudo aqui parte das páginas que o leitor pode ver, para que títulos de
páginas privadas nunca apareçam em links, contagens ou citações.
"""

from __future__ import annotations

import re
from collections import Counter

from sqlmodel import Session, select

from .models import Page, PageBlock, PageBlockType, PageTagLink, Tag, User
from .permissions import list_accessible_pages

# [[Título]] ou [[Título|texto exibido]]
WIKILINK_RE = re.compile(r"\[\[([^\[\]|\n]{1,200})(?:\|([^\[\]\n]{1,200}))?\]\]")


def normalize_title(title: str) -> str:
    return " ".join(title.split()).casefold()


def wiki_index(pages: list[Page], current_user: User) -> dict[str, int]:
    """Mapa título normalizado → id, preferindo páginas do próprio leitor."""
    index: dict[str, int] = {}
    ordered = sorted(pages, key=lambda page: (page.author_id != current_user.id, page.id))
    for page in ordered:
        index.setdefault(normalize_title(page.title), page.id)
    return index


def page_tags_counts(session: Session, pages: list[Page], limit: int = 15) -> list[tuple[Tag, int]]:
    page_ids = [page.id for page in pages]
    if not page_ids:
        return []
    links = session.exec(select(PageTagLink).where(PageTagLink.page_id.in_(page_ids))).all()
    counts = Counter(link.tag_id for link in links)
    tags = {tag.id: tag for tag in session.exec(select(Tag).where(Tag.id.in_(list(counts)))).all()}
    ranked = sorted(counts.items(), key=lambda item: (-item[1], tags[item[0]].name.casefold()))
    return [(tags[tag_id], count) for tag_id, count in ranked[:limit]]


def tag_panel_context(session: Session, tag: Tag, current_user: User) -> dict:
    accessible = list_accessible_pages(session, current_user.id)
    tagged_ids = {
        link.page_id
        for link in session.exec(select(PageTagLink).where(PageTagLink.tag_id == tag.id)).all()
    }
    pages = sorted(
        (page for page in accessible if page.id in tagged_ids),
        key=lambda page: page.updated_at,
        reverse=True,
    )
    related = [
        (item, count) for item, count in page_tags_counts(session, pages, limit=12) if item.id != tag.id
    ]
    return {"tag": tag, "tag_pages": pages, "related_tags": related}


def backlinks(session: Session, page: Page, current_user: User) -> list[Page]:
    """Páginas visíveis ao leitor que citam esta com [[Título]]."""
    target = normalize_title(page.title)
    accessible = {item.id: item for item in list_accessible_pages(session, current_user.id)}
    accessible.pop(page.id, None)
    if not accessible:
        return []
    blocks = session.exec(
        select(PageBlock).where(
            PageBlock.page_id.in_(list(accessible)),
            PageBlock.block_type == PageBlockType.TEXT,
            PageBlock.content.contains("[["),
        )
    ).all()
    found: dict[int, Page] = {}
    for block in blocks:
        if block.page_id in found:
            continue
        for match in WIKILINK_RE.finditer(block.content or ""):
            if normalize_title(match.group(1)) == target:
                found[block.page_id] = accessible[block.page_id]
                break
    return sorted(found.values(), key=lambda item: item.title.casefold())
