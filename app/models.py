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

   # pages: List["Page"] = Relationship(back_populates="author")
   # comments: List["Comment"] = Relationship(back_populates="author")
   # examples: List["CodeExample"] = Relationship(back_populates="author")


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

  #  pages: List["Page"] = Relationship(back_populates="language")


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

 #   pages: List["Page"] = Relationship(back_populates="tags", link_model=PageTagLink)


class TagCreate(TagBase):
    pass


class TagRead(TagBase):
    id: int
    created_at: datetime
    updated_at: datetime


class TagUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    slug: Optional[str] = Field(default=None, max_length=60)


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


class Page(PageBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))

 #   language: Optional[Language] = Relationship(back_populates="pages")
  #  author: Optional[User] = Relationship(back_populates="pages")
   # tags: List[Tag] = Relationship(back_populates="pages", link_model=PageTagLink)
   # comments: List["Comment"] = Relationship(back_populates="page")
#    examples: List["CodeExample"] = Relationship(back_populates="page")


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
    tag_ids: Optional[List[int]] = None


class PageRead(PageBase):
    id: int
    created_at: datetime
    updated_at: datetime
    language: Optional[LanguageRead] = None
    author: Optional[UserRead] = None
    tags: List[TagRead] = Field(default_factory=list)


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

   # page: Optional[Page] = Relationship(back_populates="comments")
  #  author: Optional[User] = Relationship(back_populates="comments")


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

 #   page: Optional[Page] = Relationship(back_populates="examples")
#    author: Optional[User] = Relationship(back_populates="examples")


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
