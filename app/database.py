from collections.abc import Generator
from pathlib import Path

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url.replace("sqlite:///", "", 1)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    ensure_sqlite_schema()


def ensure_sqlite_schema() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    required_columns = {
        "forumboard": {
            "course_name": "VARCHAR DEFAULT ''",
            "popup_enabled": "BOOLEAN DEFAULT 0",
            "updated_at": "DATETIME",
        },
    }
    with engine.begin() as connection:
        inspector = inspect(connection)
        for table_name, columns in required_columns.items():
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in columns.items():
                if column_name not in existing:
                    connection.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                    )


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
