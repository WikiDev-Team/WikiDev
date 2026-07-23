from __future__ import annotations

import os

from sqlalchemy import inspect, text
from sqlmodel import SQLModel, Session, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wikidev.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def _migrate_sqlite_page_visibility() -> None:
    """Migração mínima para bancos SQLite criados antes da visibilidade.

    O projeto ainda não usa Alembic. Portanto, adicionamos a única coluna nova em
    bancos existentes sem apagar dados. Páginas antes publicadas continuam
    públicas; as demais começam privadas.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "page" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("page")}
    if "visibility" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE page "
                "ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'PRIVATE'"
            )
        )
        connection.execute(
            text(
                "UPDATE page SET visibility = 'PUBLIC' "
                "WHERE status IN ('PUBLISHED', 'published')"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_page_visibility "
                "ON page (visibility)"
            )
        )


def _migrate_sqlite_comments() -> None:
    """Adiciona campos opcionais sem apagar comentários existentes."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "comment" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("comment")}
    with engine.begin() as connection:
        if "block_id" not in columns:
            connection.execute(
                text("ALTER TABLE comment ADD COLUMN block_id INTEGER REFERENCES pageblock(id)")
            )
        if "code" not in columns:
            connection.execute(text("ALTER TABLE comment ADD COLUMN code TEXT"))
        if "language" not in columns:
            connection.execute(
                text("ALTER TABLE comment ADD COLUMN language VARCHAR(20)")
            )


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _migrate_sqlite_page_visibility()
    _migrate_sqlite_comments()


def get_session():
    with Session(engine) as session:
        yield session
