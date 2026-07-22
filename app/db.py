from __future__ import annotations

import os

from sqlalchemy import event, inspect, text
from sqlmodel import SQLModel, Session, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wikidev.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _migrate_sqlite_schema() -> None:
    """Small, idempotent migrations for databases created before v1.1.

    Alembic is the recommended next step. This keeps existing local databases usable
    while the project is still in its prototype phase.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "folder" not in inspector.get_table_names():
        return

    folder_columns = {column["name"] for column in inspector.get_columns("folder")}
    with engine.begin() as connection:
        if "visibility" not in folder_columns:
            connection.execute(
                text(
                    "ALTER TABLE folder "
                    "ADD COLUMN visibility VARCHAR(7) NOT NULL DEFAULT 'PRIVATE'"
                )
            )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_folder_visibility ON folder (visibility)")
        )


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _migrate_sqlite_schema()


def get_session():
    with Session(engine) as session:
        yield session
