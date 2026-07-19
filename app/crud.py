from __future__ import annotations
from sqlmodel import Session, select
from sqlalchemy import delete
from .security import get_password_hash  # para rodar a funcao trocada

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
        font_size=data.font_size,
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

COMMENT_LANGUAGES = frozenset({"python", "java", "c", "cpp"})
MAX_COMMENT_REPLY_LEVELS = 4


def _normalize_comment_content(
    body: str,
    code: str | None,
    language: str | None,
) -> tuple[str, str | None, str | None]:
    normalized_body = body.strip()
    if not normalized_body:
        raise ValueError("O texto do comentário é obrigatório")

    normalized_code = code.strip() if code and code.strip() else None
    if normalized_code is None:
        return normalized_body, None, None

    normalized_language = language.strip().lower() if language else None
    if normalized_language not in COMMENT_LANGUAGES:
        raise ValueError("A linguagem é obrigatória e deve ser python, java, c ou cpp")
    return normalized_body, normalized_code, normalized_language


def get_comment_depth(session: Session, comment: Comment) -> int:
    """Retorna 0 para a raiz e detecta ciclos na cadeia de comentários."""
    depth = 0
    seen_ids = {comment.id}
    parent_id = comment.parent_comment_id
    while parent_id is not None:
        if parent_id in seen_ids:
            raise ValueError("Referência circular entre comentários")
        seen_ids.add(parent_id)
        parent = session.get(Comment, parent_id)
        if parent is None:
            raise ValueError("Comentário pai não encontrado")
        depth += 1
        parent_id = parent.parent_comment_id
    return depth


def _validate_comment_relations(session: Session, data: CommentCreate) -> None:
    if session.get(Page, data.page_id) is None:
        raise ValueError("Página não encontrada")

    if data.block_id is not None:
        block = session.get(PageBlock, data.block_id)
        if block is None:
            raise ValueError("Bloco não encontrado")
        if block.page_id != data.page_id:
            raise ValueError("O bloco não pertence à página informada")

    if data.parent_comment_id is None:
        return
    parent = session.get(Comment, data.parent_comment_id)
    if parent is None:
        raise ValueError("Comentário pai não encontrado")
    if parent.is_deleted:
        raise ValueError("Não é possível responder a um comentário excluído")
    if parent.page_id != data.page_id:
        raise ValueError("A resposta deve pertencer à mesma página")
    if parent.block_id != data.block_id:
        raise ValueError("A resposta deve pertencer à mesma discussão de bloco")
    if get_comment_depth(session, parent) >= MAX_COMMENT_REPLY_LEVELS:
        raise ValueError("O limite de quatro níveis de resposta foi atingido")


def create_comment(
    session: Session,
    data: CommentCreate,
    *,
    author_id: int,
) -> Comment:
    if session.get(User, author_id) is None:
        raise ValueError("Autor não encontrado")
    _validate_comment_relations(session, data)
    body, code, language = _normalize_comment_content(
        data.body, data.code, data.language
    )
    obj = Comment(
        page_id=data.page_id,
        block_id=data.block_id,
        parent_comment_id=data.parent_comment_id,
        author_id=author_id,
        body=body,
        code=code,
        language=language,
    )
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def update_comment(session: Session, obj: Comment, data: CommentUpdate) -> Comment:
    if obj.is_deleted:
        raise ValueError("Um comentário excluído não pode ser editado")
    payload = data.model_dump(exclude_unset=True)
    body, code, language = _normalize_comment_content(
        payload.get("body", obj.body),
        payload.get("code", obj.code),
        payload.get("language", obj.language),
    )
    obj.body = body
    obj.code = code
    obj.language = language
    _touch_update(obj)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj


def delete_comment(session: Session, obj: Comment) -> Comment:
    obj.is_deleted = True
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
