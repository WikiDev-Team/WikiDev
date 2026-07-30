
from datetime import datetime
from enum import Enum
import re
import unicodedata
from typing import List, Optional

from sqlalchemy import CheckConstraint, Column, DateTime, UniqueConstraint
from pydantic import ConfigDict
from sqlmodel import Field, Relationship, SQLModel


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


class PageBlockType(str, Enum):
    TEXT = "text"
    CODE = "code"


class FriendshipStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class PageVisibility(str, Enum):
    PRIVATE = "private"
    FRIENDS = "friends"
    PUBLIC = "public"
    CUSTOM = "custom"


class PageSharePermission(str, Enum):
    VIEW = "view"
    EDIT = "edit"


class EditPolicy(str, Enum):
    OWNER = "owner"
    VIEWERS = "viewers"
    CUSTOM = "custom"


class FolderVisibility(str, Enum):
    PRIVATE = "private"
    FRIENDS = "friends"
    PUBLIC = "public"
    CUSTOM = "custom"

# ── User ─────────────────────────────────────────────────────────────────────

class UserBase(SQLModel):
    username: str = Field(index=True, unique=True, min_length=3, max_length=50)
    email: str = Field(index=True, unique=True, min_length=3, max_length=255)
    display_name: str = Field(default="", max_length=120)
    bio: str = Field(default="")
    avatar_url: str = Field(default="")


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str = Field(default="")
    # Guarda apenas SHA-256 do cookie de sessão, nunca o token utilizável.
    token: Optional[str] = Field(default=None, index=True, max_length=64)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))

    pages: List["Page"] = Relationship(back_populates="author")
    comments: List["Comment"] = Relationship(back_populates="author")
    examples: List["CodeExample"] = Relationship(back_populates="author")
    folders: List["Folder"] = Relationship(back_populates="author")


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime


class UserPublicRead(SQLModel):
    id: int
    username: str
    display_name: str
    bio: str
    avatar_url: str
    created_at: datetime


class UserUpdate(SQLModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    email: Optional[str] = Field(default=None, min_length=3, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=120)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None


class PasswordResetToken(SQLModel, table=True):
    """Token de redefinição armazenado como hash, com expiração e uso único."""

    __table_args__ = (UniqueConstraint("token_hash", name="uq_password_reset_token_hash"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    token_hash: str = Field(index=True, max_length=64)
    expires_at: datetime = Field(sa_column=Column(DateTime, nullable=False))
    used_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))


# ── Friendship ───────────────────────────────────────────────────────────────

class Friendship(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_direction"),
        CheckConstraint("requester_id != addressee_id", name="ck_friendship_distinct_users"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    requester_id: int = Field(foreign_key="user.id", index=True)
    addressee_id: int = Field(foreign_key="user.id", index=True)
    status: FriendshipStatus = Field(default=FriendshipStatus.PENDING, index=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))


class FriendshipRead(SQLModel):
    id: int
    requester_id: int
    addressee_id: int
    status: FriendshipStatus
    created_at: datetime
    updated_at: datetime


# ── Language ─────────────────────────────────────────────────────────────────

class LanguageBase(SQLModel):
    name: str = Field(index=True, min_length=1, max_length=80)
    slug: str = Field(default="", index=True, max_length=90, unique=True)
    description: str = Field(default="")
    official_url: str = Field(default="")
    logo_url: str = Field(default="")


class Language(LanguageBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))

    pages: List["Page"] = Relationship(back_populates="language")


class LanguageCreate(LanguageBase):
    pass


class LanguageRead(LanguageBase):
    id: int
    created_at: datetime
    updated_at: datetime


class LanguageUpdate(SQLModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    slug: Optional[str] = Field(default=None, max_length=90)
    description: Optional[str] = None
    official_url: Optional[str] = None
    logo_url: Optional[str] = None


# ── Tag ──────────────────────────────────────────────────────────────────────

class TagBase(SQLModel):
    name: str = Field(index=True, min_length=1, max_length=50)
    slug: str = Field(default="", index=True, max_length=60, unique=True)


class PageTagLink(SQLModel, table=True):
    page_id: Optional[int] = Field(default=None, foreign_key="page.id", primary_key=True)
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)


class Tag(TagBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))

    pages: List["Page"] = Relationship(back_populates="tags", link_model=PageTagLink)


class TagCreate(TagBase):
    pass


class TagRead(TagBase):
    id: int
    created_at: datetime
    updated_at: datetime


class TagUpdate(SQLModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    slug: Optional[str] = Field(default=None, max_length=60)


# ── Folder ───────────────────────────────────────────────────────────────────

class FolderBase(SQLModel):
    name: str = Field(index=True, min_length=1, max_length=150)
    slug: str = Field(default="", index=True, max_length=170, unique=True)
    description: str = Field(default="")
    visibility: FolderVisibility = Field(default=FolderVisibility.PRIVATE, index=True)
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    parent_folder_id: Optional[int] = Field(default=None, foreign_key="folder.id")


class Folder(FolderBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))

    author: Optional[User] = Relationship(back_populates="folders")
    pages: List["Page"] = Relationship(back_populates="folder")


class FolderCreate(FolderBase):
    pass


class FolderRead(FolderBase):
    id: int
    created_at: datetime
    updated_at: datetime
    author: Optional[UserPublicRead] = None


class FolderUpdate(SQLModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    slug: Optional[str] = Field(default=None, max_length=170)
    description: Optional[str] = None
    visibility: Optional[FolderVisibility] = None
    parent_folder_id: Optional[int] = None

class FolderShare(SQLModel, table=True):
    folder_id: int = Field(
        foreign_key="folder.id",
        primary_key=True,
    )
    user_id: int = Field(
        foreign_key="user.id",
        primary_key=True,
    )
    created_at: datetime = Field(
        default_factory=now_utc,
        sa_column=Column(DateTime, nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=now_utc,
        sa_column=Column(DateTime, nullable=False),
    )

# ── Page ─────────────────────────────────────────────────────────────────────

class PageBase(SQLModel):
    title: str = Field(index=True, min_length=1, max_length=200)
    slug: str = Field(default="", index=True, unique=True, max_length=220)
    page_type: PageType = Field(default=PageType.PERSONAL)
    status: PageStatus = Field(default=PageStatus.DRAFT)
    visibility: PageVisibility = Field(default=PageVisibility.PRIVATE, index=True)
    edit_policy: EditPolicy = Field(default=EditPolicy.OWNER, index=True)
    summary: str = Field(default="")
    language_id: Optional[int] = Field(default=None, foreign_key="language.id")
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    parent_page_id: Optional[int] = Field(default=None, foreign_key="page.id")
    folder_id: Optional[int] = Field(default=None, foreign_key="folder.id")


class Page(PageBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))

    language: Optional[Language] = Relationship(back_populates="pages")
    author: Optional[User] = Relationship(back_populates="pages")
    tags: List[Tag] = Relationship(back_populates="pages", link_model=PageTagLink)
    comments: List["Comment"] = Relationship(back_populates="page")
    examples: List["CodeExample"] = Relationship(back_populates="page")
    blocks: List["PageBlock"] = Relationship(back_populates="page")
    folder: Optional[Folder] = Relationship(back_populates="pages")


class PageCreate(PageBase):
    tag_ids: List[int] = Field(default_factory=list)


class PageUpdate(SQLModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    slug: Optional[str] = Field(default=None, max_length=220)
    page_type: Optional[PageType] = None
    status: Optional[PageStatus] = None
    visibility: Optional[PageVisibility] = None
    edit_policy: Optional[EditPolicy] = None
    summary: Optional[str] = None
    language_id: Optional[int] = None
    parent_page_id: Optional[int] = None
    folder_id: Optional[int] = None
    tag_ids: Optional[List[int]] = None


class PageRead(PageBase):
    id: int
    created_at: datetime
    updated_at: datetime
    language: Optional[LanguageRead] = None
    author: Optional[UserPublicRead] = None
    tags: List[TagRead] = Field(default_factory=list)
    folder: Optional[FolderRead] = None


class PageShare(SQLModel, table=True):
    page_id: int = Field(foreign_key="page.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    permission: PageSharePermission = Field(default=PageSharePermission.VIEW)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))


class PageShareRead(SQLModel):
    page_id: int
    user_id: int
    permission: PageSharePermission
    created_at: datetime
    updated_at: datetime


# ── PageBlock ────────────────────────────────────────────────────────────────

class PageBlockBase(SQLModel):
    page_id: int = Field(foreign_key="page.id")
    position: int = Field(default=0, index=True)
    block_type: PageBlockType = Field(default=PageBlockType.TEXT)
    content: str = Field(default="")
    language: str = Field(default="", max_length=50)
    font_size: str = Field(default="normal", max_length=20)


class PageBlock(PageBlockBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))

    page: Optional[Page] = Relationship(back_populates="blocks")
    comments: List["Comment"] = Relationship(back_populates="block")


class PageBlockCreate(SQLModel):
    block_type: PageBlockType = Field(default=PageBlockType.TEXT)
    content: str = Field(default="")
    language: str = Field(default="", max_length=50)
    position: Optional[int] = None
    font_size: str = Field(default="normal", max_length=20)


class PageBlockRead(PageBlockBase):
    id: int
    created_at: datetime
    updated_at: datetime


class PageBlockUpdate(SQLModel):
    position: Optional[int] = None
    block_type: Optional[PageBlockType] = None
    content: Optional[str] = None
    language: Optional[str] = Field(default=None, max_length=50)
    font_size: Optional[str] = Field(default=None, max_length=20)


# ── Comment ──────────────────────────────────────────────────────────────────

class CommentBase(SQLModel):
    page_id: int = Field(foreign_key="page.id")
    author_id: Optional[int] = Field(default=None, foreign_key="user.id")
    block_id: Optional[int] = Field(default=None, foreign_key="pageblock.id", index=True)
    parent_comment_id: Optional[int] = Field(default=None, foreign_key="comment.id")
    body: str = Field(default="")
    code: Optional[str] = Field(default=None)
    language: Optional[str] = Field(default=None, max_length=20)
    is_deleted: bool = Field(default=False)


class Comment(CommentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=now_utc, sa_column=Column(DateTime, nullable=False))

    page: Optional[Page] = Relationship(back_populates="comments")
    author: Optional[User] = Relationship(back_populates="comments")
    block: Optional[PageBlock] = Relationship(back_populates="comments")


class CommentCreate(SQLModel):
    """Dados que um cliente pode enviar ao criar um comentário."""

    model_config = ConfigDict(extra="forbid")

    page_id: int
    block_id: Optional[int] = None
    parent_comment_id: Optional[int] = None
    body: str
    code: Optional[str] = None
    language: Optional[str] = Field(default=None, max_length=20)


class CommentRead(CommentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    author: Optional[UserPublicRead] = None


class CommentUpdate(SQLModel):
    model_config = ConfigDict(extra="forbid")

    body: Optional[str] = None
    code: Optional[str] = None
    language: Optional[str] = Field(default=None, max_length=20)


# ── CodeExample ──────────────────────────────────────────────────────────────

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

    page: Optional[Page] = Relationship(back_populates="examples")
    author: Optional[User] = Relationship(back_populates="examples")


class CodeExampleCreate(CodeExampleBase):
    pass


class CodeExampleRead(CodeExampleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    author: Optional[UserPublicRead] = None


class CodeExampleUpdate(SQLModel):
    title: Optional[str] = Field(default=None, max_length=200)
    code: Optional[str] = None
    explanation: Optional[str] = None
    language_hint: Optional[str] = Field(default=None, max_length=50)
    is_public: Optional[bool] = None


User.model_rebuild()
Folder.model_rebuild()
Page.model_rebuild()
Comment.model_rebuild()
CodeExample.model_rebuild()
PageBlock.model_rebuild()
