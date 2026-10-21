from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
import threading
from typing import Generator

# SQLite engine configuration
connect_args = {"check_same_thread": False}
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args
)

# Concurrency lock for booking operations to prevent race conditions & double-booking
booking_lock = threading.Lock()


def init_db() -> None:
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency that provides a database session."""
    with Session(engine) as session:
        yield session
