from __future__ import annotations

from datetime import datetime
from enum import Enum
import re
import unicodedata
from typing import Optional, List

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


def now_utc() -> datetime:
    return datetime.utcnow()


def slugify_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "item"


class PageType(str, Enum):
    OFFICIAL = "official"
    PERSONAL = "personal"
    QUESTION = "question"
    EXAMPLE = "example"
    NOTE = "note"


class PageStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# ── User ─────────────────────────────────────────────────────────────────────

class UserBase(SQLModel):
    username: str = Field(index=True, max_length=50)
    email: str = Field(index=True, max_length=255)
    display_name: str = Field(default="", max_length=120)
    bio: str = Field(default="")
    avatar_url: str = Field(default="")


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))


class UserCreate(UserBase):
    pass


class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime


class UserUpdate(SQLModel):
    username: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=120)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


# ── Language ─────────────────────────────────────────────────────────────────

class LanguageBase(SQLModel):
    name: str = Field(index=True, max_length=80)
    slug: str = Field(default="", index=True, max_length=90)
    description: str = Field(default="")
    official_url: str = Field(default="")
    logo_url: str = Field(default="")


class Language(LanguageBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))


class LanguageCreate(LanguageBase):
    pass


class LanguageRead(LanguageBase):
    id: int
    created_at: datetime
    updated_at: datetime


class LanguageUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=80)
    slug: Optional[str] = Field(default=None, max_length=90)
    description: Optional[str] = None
    official_url: Optional[str] = None
    logo_url: Optional[str] = None


# ── Tag ──────────────────────────────────────────────────────────────────────

class TagBase(SQLModel):
    name: str = Field(index=True, max_length=50)
    slug: str = Field(default="", index=True, max_length=60)


class PageTagLink(SQLModel, table=True):
    page_id: Optional[int] = Field(default=None, foreign_key="page.id", primary_key=True)
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)


class Tag(TagBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))


class TagCreate(TagBase):
    pass


class TagRead(TagBase):
    id: int
    created_at: datetime
    updated_at: datetime


class TagUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    slug: Optional[str] = Field(default=None, max_length=60)


# ── Folder ───────────────────────────────────────────────────────────────────

class FolderBase(SQLModel):
    name: str = Field(index=True, max_length=150)
    slug: str = Field(default="", index=True, max_length=170)
    description: str = Field(default="")
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    parent_folder_id: Optional[int] = Field(default=None, foreign_key="folder.id")


class Folder(FolderBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))


class FolderCreate(FolderBase):
    pass


class FolderRead(FolderBase):
    id: int
    created_at: datetime
    updated_at: datetime
    author: Optional[UserRead] = None


class FolderUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=150)
    slug: Optional[str] = Field(default=None, max_length=170)
    description: Optional[str] = None
    author_id: Optional[int] = None
    parent_folder_id: Optional[int] = None


# ── Page ─────────────────────────────────────────────────────────────────────

class PageBase(SQLModel):
    title: str = Field(index=True, max_length=200)
    slug: str = Field(default="", index=True, max_length=220)
    page_type: PageType = Field(default=PageType.PERSONAL)
    status: PageStatus = Field(default=PageStatus.DRAFT)
    summary: str = Field(default="")
    content: str = Field(default="")
    language_id: Optional[int] = Field(default=None, foreign_key="language.id")
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    parent_page_id: Optional[int] = Field(default=None, foreign_key="page.id")
    folder_id: Optional[int] = Field(default=None, foreign_key="folder.id")


class Page(PageBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))


class PageCreate(PageBase):
    tag_ids: List[int] = Field(default_factory=list)


class PageUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=200)
    slug: Optional[str] = Field(default=None, max_length=220)
    page_type: Optional[PageType] = None
    status: Optional[PageStatus] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    language_id: Optional[int] = None
    author_id: Optional[int] = None
    parent_page_id: Optional[int] = None
    folder_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None


class PageRead(PageBase):
    id: int
    created_at: datetime
    updated_at: datetime
    language: Optional[LanguageRead] = None
    author: Optional[UserRead] = None
    tags: List[TagRead] = Field(default_factory=list)
    folder: Optional[FolderRead] = None


# ── Comment ───────────────────────────────────────────────────────────────────

class CommentBase(SQLModel):
    page_id: int = Field(foreign_key="page.id")
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    parent_comment_id: Optional[int] = Field(default=None, foreign_key="comment.id")
    body: str = Field(default="")
    is_deleted: bool = Field(default=False)


class Comment(CommentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))


class CommentCreate(CommentBase):
    pass


class CommentRead(CommentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    author: Optional[UserRead] = None


class CommentUpdate(SQLModel):
    body: Optional[str] = None
    is_deleted: Optional[bool] = None


# ── CodeExample ───────────────────────────────────────────────────────────────

class CodeExampleBase(SQLModel):
    page_id: int = Field(foreign_key="page.id")
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    title: str = Field(default="", max_length=200)
    code: str = Field(default="")
    explanation: str = Field(default="")
    language_hint: str = Field(default="", max_length=50)
    is_public: bool = Field(default=True)


class CodeExample(CodeExampleBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))


class CodeExampleCreate(CodeExampleBase):
    pass


class CodeExampleRead(CodeExampleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    author: Optional[UserRead] = None


class CodeExampleUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=200)
    code: Optional[str] = None
    explanation: Optional[str] = None
    language_hint: Optional[str] = Field(default=None, max_length=50)
    is_public: Optional[bool] = None
