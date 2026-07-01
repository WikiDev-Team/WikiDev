from __future__ import annotations
from sqlmodel import Session, select
from sqlalchemy import delete
from typing import Iterable, Optional, TypeVar, Type, Any
from .security import get_password_hash #para rodar a funcao trocada
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from .models import (
    CodeExample, CodeExampleCreate, CodeExampleUpdate,
    Comment, CommentCreate, CommentUpdate,
    Folder, FolderCreate, FolderUpdate,
    Language, LanguageCreate, LanguageUpdate,
    Page, PageCreate, PageUpdate, PageTagLink,
    Tag, TagCreate, TagUpdate,
    User, UserCreate, UserUpdate,
    slugify_text,
    PageBlock, PageBlockCreate, PageBlockUpdate,
)

ModelT = TypeVar("ModelT")


def _unique_slug(session: Session, model: type, base_slug: str, exclude_id: int | None = None) -> str:
    slug = base_slug
    counter = 2
    while True:
        stmt = select(model).where(model.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(model.id != exclude_id)
        existing = session.exec(stmt).first()
        if existing is None:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def _touch_update(obj) -> None:
    from datetime import datetime
    obj.updated_at = datetime.utcnow()


# ── User ─────────────────────────────────────────────────────────────────────

def create_user(session: Session, data: UserCreate) -> User:
    payload = data.model_dump(exclude={"password"})

    obj = User(
        **payload,
        hashed_password=get_password_hash(data.password)
    )

    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj

def update_user(session: Session, obj: User, data: UserUpdate) -> User:
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(obj, key, value)
    _touch_update(obj)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


# ── Language ─────────────────────────────────────────────────────────────────

def create_language(session: Session, data: LanguageCreate) -> Language:
    obj = Language.model_validate(data)
    if not obj.slug:
        obj.slug = _unique_slug(session, Language, slugify_text(obj.name))
    else:
        obj.slug = _unique_slug(session, Language, slugify_text(obj.slug))
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_language(session: Session, obj: Language, data: LanguageUpdate) -> Language:
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        if value is not None:
            setattr(obj, key, value)
    if "name" in payload and not payload.get("slug"):
        obj.slug = _unique_slug(session, Language, slugify_text(obj.name), exclude_id=obj.id)
    elif payload.get("slug"):
        obj.slug = _unique_slug(session, Language, slugify_text(obj.slug), exclude_id=obj.id)
    _touch_update(obj)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


# ── Tag ──────────────────────────────────────────────────────────────────────

def create_tag(session: Session, data: TagCreate) -> Tag:
    obj = Tag.model_validate(data)
    if not obj.slug:
        obj.slug = _unique_slug(session, Tag, slugify_text(obj.name))
    else:
        obj.slug = _unique_slug(session, Tag, slugify_text(obj.slug))
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_tag(session: Session, obj: Tag, data: TagUpdate) -> Tag:
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        if value is not None:
            setattr(obj, key, value)
    if "name" in payload and not payload.get("slug"):
        obj.slug = _unique_slug(session, Tag, slugify_text(obj.name), exclude_id=obj.id)
    elif payload.get("slug"):
        obj.slug = _unique_slug(session, Tag, slugify_text(obj.slug), exclude_id=obj.id)
    _touch_update(obj)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


# ── Folder ───────────────────────────────────────────────────────────────────

def create_folder(session: Session, data: FolderCreate) -> Folder:
    obj = Folder.model_validate(data)
    if not obj.slug:
        obj.slug = _unique_slug(session, Folder, slugify_text(obj.name))
    else:
        obj.slug = _unique_slug(session, Folder, slugify_text(obj.slug))
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_folder(session: Session, obj: Folder, data: FolderUpdate) -> Folder:
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        setattr(obj, key, value)
    if "name" in payload and not payload.get("slug"):
        obj.slug = _unique_slug(session, Folder, slugify_text(obj.name), exclude_id=obj.id)
    elif payload.get("slug"):
        obj.slug = _unique_slug(session, Folder, slugify_text(obj.slug), exclude_id=obj.id)
    _touch_update(obj)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


# ── Page ─────────────────────────────────────────────────────────────────────

def create_page(session: Session, data: PageCreate) -> Page:
    payload = data.model_dump(exclude={"tag_ids"}, exclude_unset=True)
    obj = Page(**payload)
    if not obj.slug:
        obj.slug = _unique_slug(session, Page, slugify_text(obj.title))
    else:
        obj.slug = _unique_slug(session, Page, slugify_text(obj.slug))
    session.add(obj)
    session.flush()
    for tag_id in data.tag_ids:
        if session.get(Tag, tag_id) is not None:
            session.add(PageTagLink(page_id=obj.id, tag_id=tag_id))
    session.commit()
    session.refresh(obj)
    return obj


def update_page(session: Session, obj: Page, data: PageUpdate) -> Page:
    payload = data.model_dump(exclude_unset=True, exclude={"tag_ids"})
    for key, value in payload.items():
        if value is not None:
            setattr(obj, key, value)
    if "title" in payload and not payload.get("slug"):
        obj.slug = _unique_slug(session, Page, slugify_text(obj.title), exclude_id=obj.id)
    elif payload.get("slug"):
        obj.slug = _unique_slug(session, Page, slugify_text(payload["slug"]), exclude_id=obj.id)
    if data.tag_ids is not None:
        session.exec(delete(PageTagLink).where(PageTagLink.page_id == obj.id))
        for tag_id in data.tag_ids:
            if session.get(Tag, tag_id) is not None:
                session.add(PageTagLink(page_id=obj.id, tag_id=tag_id))
    _touch_update(obj)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


# ── PageBlock ────────────────────────────────────────────────────────────────

def get_next_block_position(session: Session, page_id: int) -> int:
    blocks = session.exec(
        select(PageBlock)
        .where(PageBlock.page_id == page_id)
        .order_by(PageBlock.position.desc())
    ).all()

    if not blocks:
        return 0

    return blocks[0].position + 1


def create_page_block(
    session: Session,
    page_id: int,
    data: PageBlockCreate,
) -> PageBlock:
    position = data.position

    if position is None:
        position = get_next_block_position(session, page_id)

    obj = PageBlock(
        page_id=page_id,
        position=position,
        block_type=data.block_type,
        content=data.content,
        language=data.language,
    )

    session.add(obj)
    session.commit()
    session.refresh(obj)

    return obj


def update_page_block(
    session: Session,
    obj: PageBlock,
    data: PageBlockUpdate,
) -> PageBlock:
    payload = data.model_dump(exclude_unset=True)

    for key, value in payload.items():
        if value is not None:
            setattr(obj, key, value)

    _touch_update(obj)

    session.add(obj)
    session.commit()
    session.refresh(obj)

    return obj


def delete_page_block(session: Session, obj: PageBlock) -> None:
    session.delete(obj)
    session.commit()

# ── Comment ───────────────────────────────────────────────────────────────────

def create_comment(session: Session, data: CommentCreate) -> Comment:
    obj = Comment.model_validate(data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_comment(session: Session, obj: Comment, data: CommentUpdate) -> Comment:
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        if value is not None:
            setattr(obj, key, value)
    _touch_update(obj)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


# ── CodeExample ───────────────────────────────────────────────────────────────

def create_code_example(session: Session, data: CodeExampleCreate) -> CodeExample:
    obj = CodeExample.model_validate(data)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_code_example(session: Session, obj: CodeExample, data: CodeExampleUpdate) -> CodeExample:
    payload = data.model_dump(exclude_unset=True)
    for key, value in payload.items():
        if value is not None:
            setattr(obj, key, value)
    _touch_update(obj)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj
