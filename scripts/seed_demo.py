from __future__ import annotations

from sqlmodel import Session, select

from app.crud import (
    create_comment,
    create_folder,
    create_language,
    create_page,
    create_page_block,
    create_tag,
    create_user,
)
from app.db import engine, init_db
from app.models import (
    Comment,
    CommentCreate,
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

        _seed_extra_pages(session, user, folder)

    print("Dados de demonstração criados. Login: admin / admin123")


def _tag_ids(session: Session, names: list[str]) -> list[int]:
    ids = []
    for name in names:
        tag = session.exec(select(Tag).where(Tag.name == name)).first()
        if tag is None:
            tag = create_tag(session, TagCreate(name=name))
        ids.append(tag.id)
    return ids


def _ensure_page(session: Session, user: User, folder: Folder | None, title: str, summary: str,
                 tags: list[str], blocks: list[tuple[PageBlockType, str, str]]) -> Page:
    page = session.exec(select(Page).where(Page.title == title)).first()
    if page is not None:
        return page
    page = create_page(
        session,
        PageCreate(
            title=title,
            page_type=PageType.NOTE,
            status=PageStatus.PUBLISHED,
            visibility=PageVisibility.PUBLIC,
            summary=summary,
            author_id=user.id,
            folder_id=folder.id if folder else None,
            tag_ids=_tag_ids(session, tags),
        ),
    )
    for block_type, content, language in blocks:
        create_page_block(
            session,
            page.id,
            PageBlockCreate(block_type=block_type, content=content, language=language),
        )
    return page


def _seed_extra_pages(session: Session, user: User, starter_folder: Folder) -> None:
    db_folder = session.exec(select(Folder).where(Folder.name == "Banco de dados")).first()
    if db_folder is None:
        db_folder = create_folder(
            session,
            FolderCreate(
                name="Banco de dados",
                description="Consultas, modelagem e dicas de SQL.",
                visibility=FolderVisibility.PUBLIC,
                author_id=user.id,
            ),
        )

    _ensure_page(
        session, user, starter_folder,
        "Git: comandos do dia a dia",
        "Cola rápida com os comandos de Git que mais aparecem no trabalho.",
        ["git", "cheatsheet"],
        [
            (PageBlockType.TEXT,
             "## Fluxo básico\n\n1. Crie uma branch a partir da `main`\n2. Faça commits pequenos e com mensagem clara\n"
             "3. Abra um **pull request** e peça revisão\n\n> Dica: use `git status` antes de qualquer comando destrutivo.", ""),
            (PageBlockType.CODE,
             "git switch -c feat/minha-feature\ngit add -p\ngit commit -m \"feat: adiciona busca por tag\"\n"
             "git push -u origin feat/minha-feature", "bash"),
        ],
    )
    joins = _ensure_page(
        session, user, db_folder,
        "SQL: tipos de JOIN",
        "Quando usar INNER, LEFT e FULL JOIN, com exemplos.",
        ["sql", "banco-de-dados"],
        [
            (PageBlockType.TEXT,
             "| JOIN | Retorna |\n|---|---|\n| `INNER` | só linhas com par nas duas tabelas |\n"
             "| `LEFT` | todas da esquerda, com `NULL` quando não há par |\n| `FULL` | todas das duas tabelas |", ""),
            (PageBlockType.CODE,
             "SELECT u.username, COUNT(p.id) AS paginas\nFROM users u\nLEFT JOIN pages p ON p.author_id = u.id\n"
             "GROUP BY u.username\nORDER BY paginas DESC;", "sql"),
        ],
    )
    _ensure_page(
        session, user, None,
        "FastAPI: rotas com dependências",
        "Como reaproveitar autenticação e sessão de banco com Depends.",
        ["python", "fastapi"],
        [
            (PageBlockType.TEXT,
             "Com `Depends`, o FastAPI resolve a sessão e o usuário antes de chamar a rota. "
             "Assim cada endpoint recebe o que precisa **sem repetir código**.", ""),
            (PageBlockType.CODE,
             "@router.get(\"/pages/{page_id}\")\ndef get_page(\n    page_id: int,\n"
             "    session: Session = Depends(get_session),\n    user: User = Depends(get_current_user),\n):\n"
             "    return require_page_view(session, page_id, user)", "python"),
        ],
    )

    has_comment = session.exec(select(Comment).where(Comment.page_id == joins.id)).first()
    if has_comment is None:
        create_comment(
            session,
            CommentCreate(page_id=joins.id, body="Vale incluir um exemplo de self join aqui também."),
            author_id=user.id,
        )


if __name__ == "__main__":
    main()
