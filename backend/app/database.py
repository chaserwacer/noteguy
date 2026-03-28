"""SQLModel database engine and session management."""

from sqlmodel import SQLModel, Session, create_engine, text

from app.config import get_settings

engine = create_engine(
    get_settings().database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Create all tables defined by SQLModel metadata."""
    SQLModel.metadata.create_all(engine)
    # Migration: add path column to folder if missing
    with engine.connect() as conn:
        columns = [
            row[1]
            for row in conn.execute(text("PRAGMA table_info(folder)")).fetchall()
        ]
        if "path" not in columns:
            conn.execute(text("ALTER TABLE folder ADD COLUMN path TEXT DEFAULT ''"))
            conn.commit()


def get_session():
    """Yield a database session for FastAPI dependency injection."""
    with Session(engine) as session:
        yield session
