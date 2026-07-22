from __future__ import annotations

from sqlmodel import Session, select

from app.crud import create_folder, create_language, create_page, create_page_block, create_tag, create_user
from app.db import engine, init_db
from app.models import (
    Folder,
    FolderCreate,
    FolderVisibility,
    Language,
    LanguageCreate,
    Page,
    PageBlockCreate,
    PageBlockType,
    PageCreate,
    PageStatus,
    PageType,
    PageVisibility,
    Tag,
    TagCreate,
    User,
    UserCreate,
)


def main() -> None:
    init_db()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "admin")).first()
        if user is None:
            user = create_user(
                session,
                UserCreate(
                    username="admin",
                    email="admin@wikidev.local",
                    display_name="Administrador",
                    bio="Conta inicial para demonstração.",
                    password="admin123",
                ),
            )

        language = session.exec(select(Language).where(Language.name == "Python")).first()
        if language is None:
            language = create_language(
                session,
                LanguageCreate(
                    name="Python",
                    description="Linguagem de propósito geral.",
                    official_url="https://www.python.org/",
                ),
            )

        tag = session.exec(select(Tag).where(Tag.name == "exemplo")).first()
        if tag is None:
            tag = create_tag(session, TagCreate(name="exemplo"))

        folder = session.exec(select(Folder).where(Folder.name == "Primeiros passos")).first()
        if folder is None:
            folder = create_folder(
                session,
                FolderCreate(
                    name="Primeiros passos",
                    description="Conteúdo de demonstração do WikiDev.",
                    visibility=FolderVisibility.PUBLIC,
                    author_id=user.id,
                ),
            )

        page = session.exec(select(Page).where(Page.title == "Python: variáveis e tipos básicos")).first()
        if page is None:
            page = create_page(
                session,
                PageCreate(
                    title="Python: variáveis e tipos básicos",
                    page_type=PageType.OFFICIAL,
                    status=PageStatus.PUBLISHED,
                    visibility=PageVisibility.PUBLIC,
                    summary="Uma introdução curta à criação de variáveis em Python.",
                    language_id=language.id,
                    author_id=user.id,
                    folder_id=folder.id,
                    tag_ids=[tag.id],
                ),
            )
            create_page_block(
                session,
                page.id,
                PageBlockCreate(
                    block_type=PageBlockType.TEXT,
                    content="Python possui tipagem dinâmica: o tipo acompanha o valor atribuído.",
                    font_size="large",
                ),
            )
            create_page_block(
                session,
                page.id,
                PageBlockCreate(
                    block_type=PageBlockType.CODE,
                    content='linguagem = "Python"\nversao = 3\nprint(linguagem, versao)',
                    language="python",
                ),
            )

    print("Dados de demonstração criados. Login: admin / admin123")


if __name__ == "__main__":
    main()
