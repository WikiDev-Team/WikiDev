from dataclasses import dataclass
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
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
    def block_label(self) -> str:
        if self.block is None:
            return "Discussão geral da página"
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

    comments = session.exec(
        select(Comment)
        .where(Comment.page_id.in_(pages_by_id), Comment.is_deleted.is_(False))
        .order_by(Comment.created_at.desc(), Comment.id.desc())
    ).all()
    groups: dict[tuple[int, int | None], list[Comment]] = {}
    for comment in comments:
        groups.setdefault((comment.page_id, comment.block_id), []).append(comment)

    entries: list[DiscussionEntry] = []
    for (page_id, block_id), group in groups.items():
        block = session.get(PageBlock, block_id) if block_id is not None else None
        if block_id is not None and (block is None or block.page_id != page_id):
            continue
        latest = group[0]
        entries.append(
            DiscussionEntry(
                page=pages_by_id[page_id],
                block=block,
                comment_count=len(group),
                latest_activity=latest.created_at,
                latest_author=session.get(User, latest.author_id),
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
            "project": "WikiDev",
            "usuario": current_user,
            "discussions": list_recent_discussions(session, current_user),
        },
    )
