"""Popula o banco com conteúdo de demonstração útil.

Uso: python -m scripts.seed_demo

Pode rodar mais de uma vez. Páginas de demonstração que já existem (mesmo
título e mesmo autor) são atualizadas para o conteúdo atual de
scripts/demo_content.py. Páginas criadas por pessoas não são tocadas.
"""

from __future__ import annotations

import os

from sqlmodel import Session, select

from app.crud import (
    create_comment,
    create_folder,
    create_page,
    create_page_block,
    create_tag,
    create_user,
    delete_page_block,
    update_folder,
    update_page,
)
from app.db import engine, init_db
from app.security import get_password_hash
from app.models import (
    Comment,
    CommentCreate,
    Folder,
    FolderCreate,
    FolderUpdate,
    FolderVisibility,
    Friendship,
    FriendshipStatus,
    Page,
    PageBlock,
    PageBlockCreate,
    PageBlockType,
    PageCreate,
    PageStatus,
    PageType,
    PageUpdate,
    PageVisibility,
    Tag,
    TagCreate,
    User,
    UserCreate,
)
from scripts.demo_content import COMMENTS, FOLDERS, PAGES, USERS


def _ensure_users(session: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    for data in USERS:
        # Em uma demonstração pública, SEED_<USUÁRIO>_PASSWORD (por exemplo
        # SEED_ADMIN_PASSWORD) troca a senha conhecida do repositório.
        override = os.getenv(f"SEED_{data['username'].upper()}_PASSWORD")
        if override:
            data = {**data, "password": override}
        user = session.exec(select(User).where(User.username == data["username"])).first()
        if user is None:
            user = create_user(session, UserCreate(**data))
        elif override:
            user.hashed_password = get_password_hash(override)
            session.add(user)
            session.commit()
        users[data["username"]] = user
    return users


def _ensure_friendship(session: Session, a: User, b: User) -> None:
    existing = session.exec(
        select(Friendship).where(
            ((Friendship.requester_id == a.id) & (Friendship.addressee_id == b.id))
            | ((Friendship.requester_id == b.id) & (Friendship.addressee_id == a.id))
        )
    ).first()
    if existing is None:
        session.add(Friendship(requester_id=a.id, addressee_id=b.id, status=FriendshipStatus.ACCEPTED))
    elif existing.status != FriendshipStatus.ACCEPTED:
        existing.status = FriendshipStatus.ACCEPTED
        session.add(existing)
    session.commit()


def _ensure_folders(session: Session, users: dict[str, User]) -> dict[str, Folder]:
    folders: dict[str, Folder] = {}
    for owner, name, description in FOLDERS:
        author = users[owner]
        folder = session.exec(
            select(Folder).where(Folder.name == name, Folder.author_id == author.id)
        ).first()
        if folder is None:
            folder = create_folder(
                session,
                FolderCreate(
                    name=name,
                    description=description,
                    visibility=FolderVisibility.PUBLIC,
                    author_id=author.id,
                ),
            )
        elif folder.description != description or folder.visibility != FolderVisibility.PUBLIC:
            folder = update_folder(
                session,
                folder,
                FolderUpdate(description=description, visibility=FolderVisibility.PUBLIC),
            )
        folders[name] = folder
    return folders


def _tag_ids(session: Session, names: list[str]) -> list[int]:
    ids = []
    for name in names:
        tag = session.exec(select(Tag).where(Tag.name == name)).first()
        if tag is None:
            tag = create_tag(session, TagCreate(name=name))
        ids.append(tag.id)
    return ids


def _block_specs(spec: dict) -> list[tuple[str, str, str]]:
    return [(block[0], block[1], block[2] if len(block) > 2 else "") for block in spec["blocks"]]


def _current_blocks(session: Session, page: Page) -> list[PageBlock]:
    return session.exec(
        select(PageBlock)
        .where(PageBlock.page_id == page.id)
        .order_by(PageBlock.position.asc(), PageBlock.id.asc())
    ).all()


def _upsert_page(session: Session, spec: dict, users: dict[str, User], folders: dict[str, Folder]) -> Page:
    author = users[spec["author"]]
    folder = folders[spec["folder"]]
    tag_ids = _tag_ids(session, spec["tags"])
    page = session.exec(
        select(Page).where(Page.title == spec["title"], Page.author_id == author.id)
    ).first()

    if page is None:
        page = create_page(
            session,
            PageCreate(
                title=spec["title"],
                page_type=PageType.NOTE,
                status=PageStatus.PUBLISHED,
                visibility=PageVisibility.PUBLIC,
                summary=spec["summary"],
                author_id=author.id,
                folder_id=folder.id,
                tag_ids=tag_ids,
            ),
        )
    else:
        page = update_page(
            session,
            page,
            PageUpdate(
                summary=spec["summary"],
                folder_id=folder.id,
                status=PageStatus.PUBLISHED,
                visibility=PageVisibility.PUBLIC,
                tag_ids=tag_ids,
            ),
        )

    wanted = _block_specs(spec)
    current = _current_blocks(session, page)
    if [(b.block_type.value, b.content, b.language or "") for b in current] != wanted:
        for block in current:
            delete_page_block(session, block)
        for position, (block_type, content, language) in enumerate(wanted):
            create_page_block(
                session,
                page.id,
                PageBlockCreate(
                    block_type=PageBlockType(block_type),
                    content=content,
                    language=language,
                    position=position,
                ),
            )
    return page


# Comentário da versão antiga do seed, substituído pelo comentário da Ana.
LEGACY_COMMENTS = {("admin", "SQL: tipos de JOIN", "Vale incluir um exemplo de self join aqui também.")}


def _ensure_comments(session: Session, users: dict[str, User], pages: dict[str, Page]) -> None:
    for username, title, body in LEGACY_COMMENTS:
        legacy = session.exec(
            select(Comment).where(
                Comment.page_id == pages[title].id,
                Comment.author_id == users[username].id,
                Comment.body == body,
                Comment.block_id.is_(None),
                Comment.parent_comment_id.is_(None),
            )
        ).first()
        has_replies = legacy is not None and session.exec(
            select(Comment).where(Comment.parent_comment_id == legacy.id)
        ).first()
        if legacy is not None and not has_replies:
            session.delete(legacy)
            session.commit()

    for username, title, body in COMMENTS:
        page = pages[title]
        author = users[username]
        exists = session.exec(
            select(Comment).where(
                Comment.page_id == page.id, Comment.author_id == author.id, Comment.body == body
            )
        ).first()
        if exists is None:
            create_comment(session, CommentCreate(page_id=page.id, body=body), author_id=author.id)


def main() -> None:
    init_db()
    with Session(engine) as session:
        users = _ensure_users(session)
        _ensure_friendship(session, users["admin"], users["ana"])
        folders = _ensure_folders(session, users)
        pages = {spec["title"]: _upsert_page(session, spec, users, folders) for spec in PAGES}
        _ensure_comments(session, users, pages)

    print("Dados de demonstração prontos.")
    for data in USERS:
        if os.getenv(f"SEED_{data['username'].upper()}_PASSWORD"):
            print(f"Login: {data['username']} (senha definida por variável de ambiente)")
        else:
            print(f"Login: {data['username']} / {data['password']}")


if __name__ == "__main__":
    main()
