
from sqlmodel import Session, select

from app.db import init_db, engine
from app.models import (
    Language, Tag, Page, User,
    PageType, PageStatus,
    LanguageCreate, TagCreate, UserCreate, PageCreate,
)
from app.crud import create_language, create_tag, create_page, create_user

def main():
    init_db()
    with Session(engine) as session:
        if session.exec(select(Language)).first() is None:
            create_language(session, LanguageCreate(
                name="Python",
                description="Linguagem de programação usada como exemplo nas páginas oficiais.",
                official_url="https://www.python.org/",
                logo_url="",
                slug="",
            ))
            create_language(session, LanguageCreate(
                name="Java",
                description="Linguagem orientada a objetos muito comum no curso.",
                official_url="https://www.java.com/",
                logo_url="",
                slug="",
            ))

        if session.exec(select(Tag)).first() is None:
            create_tag(session, TagCreate(name="sintaxe", slug=""))
            create_tag(session, TagCreate(name="bibliotecas", slug=""))
            create_tag(session, TagCreate(name="exemplo", slug=""))

        if session.exec(select(User)).first() is None:
            create_user(session, UserCreate(
                username="admin",
                email="admin@wikidev.local",
                display_name="Administrador",
                bio="Conta inicial para testes.",
                avatar_url="",
            ))

        if session.exec(select(Page)).first() is None:
            user = session.exec(select(User).where(User.username == "admin")).first()
            language = session.exec(select(Language).where(Language.name == "Python")).first()
            tags = session.exec(select(Tag).where(Tag.name.in_(["sintaxe", "exemplo"]))).all()
            page = create_page(session, PageCreate(
                title="Python - variáveis e tipos básicos",
                page_type=PageType.OFFICIAL,
                status=PageStatus.PUBLISHED,
                summary="Página oficial inicial com conteúdo sintático.",
                content="Conteúdo de demonstração.",
                language_id=language.id if language else None,
                author_id=user.id if user else None,
                parent_page_id=None,
                slug="",
                tag_ids=[tag.id for tag in tags if tag.id is not None],
            ))
            session.refresh(page)

if __name__ == "__main__":
    main()
