from __future__ import annotations

from sqlmodel import Session

from app.crud import create_folder, create_page, create_page_block, create_user, update_page
from app.models import FolderCreate, PageBlockCreate, PageBlockType, PageCreate, PageUpdate, UserCreate
from app.security import verify_password


def test_crud_hashes_password_generates_unique_slugs_and_keeps_font_size(session: Session):
    user = create_user(
        session,
        UserCreate(username="grace", email="grace@example.com", password="senha-segura"),
    )
    assert user.hashed_password != "senha-segura"
    assert verify_password("senha-segura", user.hashed_password)

    first = create_page(session, PageCreate(title="Estruturas de Dados", author_id=user.id))
    second = create_page(session, PageCreate(title="Estruturas de Dados", author_id=user.id))
    assert first.slug == "estruturas-de-dados"
    assert second.slug == "estruturas-de-dados-2"

    block = create_page_block(
        session,
        first.id,
        PageBlockCreate(
            block_type=PageBlockType.TEXT,
            content="Introdução",
            font_size="large",
        ),
    )
    assert block.position == 0
    assert block.font_size == "large"

    second_block = create_page_block(
        session,
        first.id,
        PageBlockCreate(block_type=PageBlockType.CODE, content="print('ok')"),
    )
    assert second_block.position == 1


def test_page_can_be_detached_from_folder_via_update(session: Session):
    user = create_user(
        session,
        UserCreate(username="linus", email="linus@example.com", password="senha-segura"),
    )
    folder = create_folder(session, FolderCreate(name="Sistemas", author_id=user.id))
    page = create_page(session, PageCreate(title="Kernel", author_id=user.id, folder_id=folder.id))
    updated = update_page(session, page, PageUpdate(folder_id=None))
    assert updated.folder_id is None
