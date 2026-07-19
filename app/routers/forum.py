from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from ..db import get_session
from ..dependencies import get_current_user
from ..models import Comment, Page, PageBlock, User
from ..permissions import list_accessible_pages
from ..templates import templates

router = APIRouter(tags=["forum"])


@dataclass
class DiscussionEntry:
    page: Page
    block: PageBlock | None
    comment_count: int
    latest_activity: datetime
    latest_author: User | None

    @property
    def url(self) -> str:
        discussion = f"block-{self.block.id}" if self.block else "page"
        return f"/dashboard?open_page={self.page.id}&discussion={discussion}"

    @property
    def block_label(self) -> str | None:
        if self.block is None:
            return None
        kind = "Código" if self.block.block_type.value == "code" else "Texto"
        excerpt = " ".join(self.block.content.split())
        if len(excerpt) > 90:
            excerpt = f"{excerpt[:87]}…"
        return f"{kind}: {excerpt}" if excerpt else f"Bloco de {kind.lower()}"


def list_recent_discussions(session: Session, current_user: User) -> list[DiscussionEntry]:
    pages = list_accessible_pages(session, current_user.id)
    pages_by_id = {page.id: page for page in pages}
    if not pages_by_id:
        return []

    activity = aliased(Comment)
    latest = aliased(Comment)
    same_block = or_(
        latest.block_id == activity.block_id,
        (latest.block_id.is_(None) & activity.block_id.is_(None)),
    )
    latest_author_id = (
        select(latest.author_id)
        .where(
            latest.page_id == activity.page_id,
            same_block,
            latest.is_deleted.is_(False),
        )
        .order_by(latest.created_at.desc(), latest.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    rows = session.exec(
        select(
            activity.page_id,
            activity.block_id,
            func.count(activity.id),
            func.max(activity.created_at),
            latest_author_id,
        )
        .where(
            activity.page_id.in_(pages_by_id),
            activity.is_deleted.is_(False),
        )
        .group_by(activity.page_id, activity.block_id)
        .order_by(func.max(activity.created_at).desc())
    ).all()

    block_ids = {block_id for _, block_id, *_ in rows if block_id is not None}
    blocks_by_id = {
        block.id: block
        for block in session.exec(select(PageBlock).where(PageBlock.id.in_(block_ids))).all()
    } if block_ids else {}
    author_ids = {author_id for *_, author_id in rows if author_id is not None}
    authors_by_id = {
        author.id: author
        for author in session.exec(select(User).where(User.id.in_(author_ids))).all()
    } if author_ids else {}

    entries: list[DiscussionEntry] = []
    for page_id, block_id, count, latest_at, author_id in rows:
        block = blocks_by_id.get(block_id) if block_id is not None else None
        if block_id is not None and block is None:
            continue
        entries.append(
            DiscussionEntry(
                page=pages_by_id[page_id],
                block=block,
                comment_count=count,
                latest_activity=latest_at,
                latest_author=authors_by_id.get(author_id),
            )
        )
    return entries


@router.get("/forum", response_class=HTMLResponse)
def forum(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        request=request,
        name="forum.html",
        context={
            "usuario": current_user,
            "discussions": list_recent_discussions(session, current_user),
        },
    )
