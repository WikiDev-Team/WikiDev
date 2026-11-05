"""Navegação da wiki: árvore lateral, breadcrumbs, favoritas, visitas e filtros da home.

Tudo aqui parte da lista de páginas que o usuário já pode ver
(`list_accessible_pages`), então filtros e ordenações nunca revelam
páginas escondidas.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import urlencode

from sqlalchemy import func
from sqlalchemy.orm import object_session
from sqlmodel import Session, select

from .models import (
    Folder,
    Page,
    PageFavorite,
    PageRevision,
    PageTagLink,
    PageVisit,
    Tag,
    User,
    now_utc,
)
from .permissions import accessible_folders, can_view_page, get_friend_ids, list_accessible_pages

# Quantos itens cada lista mostra antes do botão "Mostrar mais".
BROWSE_PAGE_SIZE = 24
TREE_PAGE_SIZE = 30
HOME_SECTION_SIZE = 5
SIDEBAR_FAVORITES = 8

OWNER_FILTERS = {
    "all": "Todas",
    "mine": "Minhas",
    "friends": "De amigos",
    "others": "De outras pessoas",
}
SORT_OPTIONS = {
    "recent": "Atualizadas recentemente",
    "alpha": "Ordem alfabética",
    "edited": "Mais editadas",
    "viewed": "Mais vistas",
}


# ── Breadcrumbs ──────────────────────────────────────────────────────────────

def folder_chain(folder: Folder | None, session: Session | None = None) -> list[Folder]:
    """Pastas da raiz até `folder` (inclusive), protegido contra ciclos."""
    if folder is None:
        return []
    session = session or object_session(folder)
    chain: list[Folder] = []
    seen: set[int] = set()
    current: Folder | None = folder
    while current is not None and current.id not in seen and len(chain) < 20:
        seen.add(current.id)
        chain.append(current)
        if current.parent_folder_id is None or session is None:
            break
        current = session.get(Folder, current.parent_folder_id)
    return list(reversed(chain))


# ── Favoritas e visitas ──────────────────────────────────────────────────────

def is_favorite(session: Session, user_id: int, page_id: int) -> bool:
    return session.get(PageFavorite, (user_id, page_id)) is not None


def toggle_favorite(session: Session, user_id: int, page_id: int) -> bool:
    """Liga/desliga a estrela e devolve o novo estado."""
    favorite = session.get(PageFavorite, (user_id, page_id))
    if favorite is None:
        session.add(PageFavorite(user_id=user_id, page_id=page_id))
        session.commit()
        return True
    session.delete(favorite)
    session.commit()
    return False


def record_page_view(session: Session, user_id: int, page_id: int) -> None:
    visit = session.get(PageVisit, (user_id, page_id))
    if visit is None:
        visit = PageVisit(user_id=user_id, page_id=page_id, count=0)
    visit.count += 1
    visit.last_viewed_at = now_utc()
    session.add(visit)
    session.commit()


def favorite_pages(session: Session, user_id: int, visible: dict[int, Page]) -> list[Page]:
    rows = session.exec(
        select(PageFavorite.page_id)
        .where(PageFavorite.user_id == user_id)
        .order_by(PageFavorite.created_at.desc())
    ).all()
    return [visible[page_id] for page_id in rows if page_id in visible]


def recently_viewed_pages(
    session: Session, user_id: int, visible: dict[int, Page], limit: int = HOME_SECTION_SIZE
) -> list[Page]:
    rows = session.exec(
        select(PageVisit.page_id)
        .where(PageVisit.user_id == user_id)
        .order_by(PageVisit.last_viewed_at.desc())
        .limit(limit * 3)
    ).all()
    return [visible[page_id] for page_id in rows if page_id in visible][:limit]


def view_counts(session: Session, page_ids: list[int]) -> dict[int, int]:
    """Total de visitas de todos os usuários, por página."""
    if not page_ids:
        return {}
    rows = session.exec(
        select(PageVisit.page_id, func.sum(PageVisit.count))
        .where(PageVisit.page_id.in_(page_ids))
        .group_by(PageVisit.page_id)
    ).all()
    return {page_id: int(total or 0) for page_id, total in rows}


def edit_counts(session: Session, page_ids: list[int]) -> dict[int, int]:
    """Quantidade de versões salvas no histórico, por página."""
    if not page_ids:
        return {}
    rows = session.exec(
        select(PageRevision.page_id, func.count(PageRevision.id))
        .where(PageRevision.page_id.in_(page_ids))
        .group_by(PageRevision.page_id)
    ).all()
    return {page_id: int(total) for page_id, total in rows}


# ── Filtros e ordenação da home ──────────────────────────────────────────────

@dataclass
class BrowseFilters:
    owner: str = "all"
    tag: str = ""
    sort: str = "recent"
    q: str = ""
    offset: int = 0

    @classmethod
    def from_params(cls, params) -> "BrowseFilters":
        owner = params.get("owner", "all")
        sort = params.get("sort", "recent")
        try:
            offset = max(0, int(params.get("offset", 0)))
        except (TypeError, ValueError):
            offset = 0
        return cls(
            owner=owner if owner in OWNER_FILTERS else "all",
            tag=(params.get("tag") or "").strip()[:60],
            sort=sort if sort in SORT_OPTIONS else "recent",
            q=(params.get("q") or "").strip()[:100],
            offset=offset,
        )

    @property
    def is_default(self) -> bool:
        return self.owner == "all" and not self.tag and self.sort == "recent" and not self.q

    def query_string(self, **overrides) -> str:
        values = {"owner": self.owner, "tag": self.tag, "sort": self.sort, "q": self.q}
        values.update(overrides)
        defaults = {"owner": "all", "sort": "recent", "tag": "", "q": "", "offset": 0}
        clean = {key: value for key, value in values.items() if value != defaults.get(key)}
        return urlencode(clean)


def _owner_group(page: Page, user_id: int, friend_ids: set[int]) -> str:
    if page.author_id == user_id:
        return "mine"
    if page.author_id in friend_ids:
        return "friends"
    return "others"


def browse_pages(
    session: Session, user: User, pages: list[Page], filters: BrowseFilters
) -> dict:
    """Aplica filtro de autoria, tag e texto, ordena e corta em uma página de resultados."""
    friend_ids = get_friend_ids(session, user.id)
    page_ids = [page.id for page in pages]

    tag_links = session.exec(
        select(PageTagLink.page_id, Tag.slug, Tag.name)
        .join(Tag, Tag.id == PageTagLink.tag_id)
        .where(PageTagLink.page_id.in_(page_ids))
    ).all() if page_ids else []
    tags_by_page: dict[int, set[str]] = defaultdict(set)
    tag_names: dict[str, str] = {}
    for page_id, slug, name in tag_links:
        tags_by_page[page_id].add(slug)
        tag_names[slug] = name

    # Contagens por autoria consideram tag e texto, para os chips dizerem o que vai aparecer.
    needle = filters.q.casefold()

    def matches_text_and_tag(page: Page) -> bool:
        if filters.tag and filters.tag not in tags_by_page.get(page.id, ()):
            return False
        if needle and needle not in page.title.casefold() and needle not in (page.summary or "").casefold():
            return False
        return True

    candidates = [page for page in pages if matches_text_and_tag(page)]
    owner_counts = {key: 0 for key in OWNER_FILTERS}
    owner_counts["all"] = len(candidates)
    for page in candidates:
        owner_counts[_owner_group(page, user.id, friend_ids)] += 1

    if filters.owner != "all":
        candidates = [
            page for page in candidates if _owner_group(page, user.id, friend_ids) == filters.owner
        ]

    ids = [page.id for page in candidates]
    edits = edit_counts(session, ids)
    views = view_counts(session, ids)
    if filters.sort == "alpha":
        candidates.sort(key=lambda page: page.title.casefold())
    elif filters.sort == "edited":
        candidates.sort(key=lambda page: (-edits.get(page.id, 0), -page.updated_at.timestamp()))
    elif filters.sort == "viewed":
        candidates.sort(key=lambda page: (-views.get(page.id, 0), -page.updated_at.timestamp()))
    else:
        candidates.sort(key=lambda page: page.updated_at, reverse=True)

    end = filters.offset + BROWSE_PAGE_SIZE
    tag_options = sorted(tag_names.items(), key=lambda item: item[1].casefold())
    return {
        "filters": filters,
        "browse_items": candidates[filters.offset:end],
        "browse_total": len(candidates),
        "browse_next_offset": end if end < len(candidates) else None,
        "owner_counts": owner_counts,
        "owner_filters": OWNER_FILTERS,
        "sort_options": SORT_OPTIONS,
        "tag_options": tag_options,
        "active_tag_name": tag_names.get(filters.tag, filters.tag),
        "edit_counts": edits,
        "view_counts": views,
        "friend_ids": friend_ids,
    }


def home_context(session: Session, user: User, pages: list[Page], filters: BrowseFilters) -> dict:
    visible = {page.id: page for page in pages}
    views = view_counts(session, list(visible))
    most_viewed = sorted(
        (page for page in pages if views.get(page.id)),
        key=lambda page: (-views[page.id], page.title.casefold()),
    )[:HOME_SECTION_SIZE]
    context = {
        "favorites": favorite_pages(session, user.id, visible),
        "recently_viewed": recently_viewed_pages(session, user.id, visible),
        "most_viewed": most_viewed,
        "most_viewed_counts": views,
    }
    context.update(browse_pages(session, user, pages, filters))
    return context


# ── Árvore lateral ───────────────────────────────────────────────────────────

def _sort_tree_pages(pages: list[Page]) -> list[Page]:
    return sorted(pages, key=lambda page: page.title.casefold())


def sidebar_context(
    session: Session,
    user: User,
    *,
    pages: list[Page] | None = None,
    folders: list[Folder] | None = None,
    open_page: Page | None = None,
    open_folder: Folder | None = None,
) -> dict:
    """Contexto da barra lateral: favoritas, árvore de pastas e páginas sem pasta.

    As pastas vêm todas (costumam ser poucas); as páginas de cada pasta só são
    renderizadas para as pastas abertas, e as demais chegam por htmx quando o
    usuário expande a pasta.
    """
    if pages is None:
        pages = list_accessible_pages(session, user.id)
    if folders is None:
        folders = accessible_folders(session, user)
    folder_ids = {folder.id for folder in folders}

    pages_by_folder: dict[int | None, list[Page]] = defaultdict(list)
    for page in pages:
        key = page.folder_id if page.folder_id in folder_ids else None
        pages_by_folder[key].append(page)

    children: dict[int | None, list[Folder]] = defaultdict(list)
    for folder in folders:
        parent = folder.parent_folder_id if folder.parent_folder_id in folder_ids else None
        children[parent].append(folder)

    # Total de páginas dentro de cada pasta, contando subpastas.
    totals: dict[int, int] = {}

    def total(folder_id: int, depth: int = 0) -> int:
        if folder_id in totals:
            return totals[folder_id]
        count = len(pages_by_folder.get(folder_id, []))
        if depth < 20:
            count += sum(total(child.id, depth + 1) for child in children.get(folder_id, []))
        totals[folder_id] = count
        return count

    for folder in folders:
        total(folder.id)

    current_folder = open_folder
    if current_folder is None and open_page is not None and open_page.folder_id in folder_ids:
        current_folder = next(folder for folder in folders if folder.id == open_page.folder_id)
    expanded = {folder.id for folder in folder_chain(current_folder, session)}

    unfiled = _sort_tree_pages(pages_by_folder.get(None, []))
    visible = {page.id: page for page in pages}
    return {
        "usuario": user,
        "pages": pages,
        "folders": folders,
        "tree_children": children,
        "tree_pages": {key: _sort_tree_pages(value) for key, value in pages_by_folder.items()},
        "tree_totals": totals,
        "tree_expanded": expanded,
        "tree_page_size": TREE_PAGE_SIZE,
        "unfiled_pages": unfiled[:TREE_PAGE_SIZE],
        "unfiled_total": len(unfiled),
        "unfiled_next_offset": TREE_PAGE_SIZE if len(unfiled) > TREE_PAGE_SIZE else None,
        "sidebar_favorites": favorite_pages(session, user.id, visible)[:SIDEBAR_FAVORITES],
        "open_page_id": open_page.id if open_page else None,
    }


def folder_tree_pages(session: Session, user: User, folder: Folder) -> list[Page]:
    """Páginas visíveis de uma pasta, em ordem alfabética (para carregar ao expandir)."""
    pages = session.exec(select(Page).where(Page.folder_id == folder.id)).all()
    return _sort_tree_pages([page for page in pages if can_view_page(session, page, user)])


def unfiled_tree_pages(session: Session, user: User) -> list[Page]:
    pages = list_accessible_pages(session, user.id)
    folder_ids = {folder.id for folder in accessible_folders(session, user)}
    return _sort_tree_pages([page for page in pages if page.folder_id not in folder_ids])


def visible_folder_path(session: Session, folder: Folder | None, user: User) -> list[Folder]:
    """Trilha de pastas para breadcrumbs, só se o usuário pode ver a pasta (e portanto as de cima)."""
    from .permissions import can_view_folder

    if folder is None or not can_view_folder(session, folder, user):
        return []
    return folder_chain(folder, session)


def page_nav_context(session: Session, page: Page, user: User) -> dict:
    """O que o cabeçalho de uma página precisa para trilha e estrela."""
    path = visible_folder_path(session, page.folder, user)
    return {
        "folder_path": path,
        "folder_chain_ids": ",".join(str(folder.id) for folder in path),
        "is_favorite": is_favorite(session, user.id, page.id),
    }
