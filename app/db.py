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
    """Migrações idempotentes enquanto o projeto ainda não usa Alembic."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        if "page" in tables:
            page_columns = {column["name"] for column in inspector.get_columns("page")}
            if "visibility" not in page_columns:
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
                text("CREATE INDEX IF NOT EXISTS ix_page_visibility ON page (visibility)")
            )
            if "edit_policy" not in page_columns:
                connection.execute(
                    text(
                        "ALTER TABLE page "
                        "ADD COLUMN edit_policy VARCHAR(20) NOT NULL DEFAULT 'owner'"
                    )
                )
                connection.execute(
                    text(
                        "UPDATE page SET edit_policy = 'custom' "
                        "WHERE visibility = 'custom' AND EXISTS ("
                        "SELECT 1 FROM pageshare "
                        "WHERE pageshare.page_id = page.id "
                        "AND pageshare.permission = 'edit'"
                        ")"
                    )
                )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_page_edit_policy ON page (edit_policy)")
            )

        if "folder" in tables:
            folder_columns = {column["name"] for column in inspector.get_columns("folder")}
            if "visibility" not in folder_columns:
                connection.execute(
                    text(
                        "ALTER TABLE folder "
                        "ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'PRIVATE'"
                    )
                )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_folder_visibility ON folder (visibility)")
            )
            if "edit_policy" not in folder_columns:
                connection.execute(
                    text(
                        "ALTER TABLE folder "
                        "ADD COLUMN edit_policy VARCHAR(20) NOT NULL DEFAULT 'owner'"
                    )
                )
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_folder_edit_policy ON folder (edit_policy)")
            )

        if "foldershare" in tables:
            folder_share_columns = {
                column["name"] for column in inspector.get_columns("foldershare")
            }
            if "permission" not in folder_share_columns:
                connection.execute(
                    text(
                        "ALTER TABLE foldershare "
                        "ADD COLUMN permission VARCHAR(20) NOT NULL DEFAULT 'view'"
                    )
                )

        if "comment" in tables:
            comment_columns = {column["name"] for column in inspector.get_columns("comment")}
            if "block_id" not in comment_columns:
                connection.execute(
                    text("ALTER TABLE comment ADD COLUMN block_id INTEGER REFERENCES pageblock(id)")
                )
            if "code" not in comment_columns:
                connection.execute(text("ALTER TABLE comment ADD COLUMN code TEXT"))
            if "language" not in comment_columns:
                connection.execute(text("ALTER TABLE comment ADD COLUMN language VARCHAR(20)"))
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_comment_block_id ON comment (block_id)")
            )


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _migrate_sqlite_schema()


def get_session():
    with Session(engine) as session:
        yield session
