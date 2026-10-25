
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def get_database_url():
    # Use separate environment variables when available
    if all(
        os.getenv(key)
        for key in (
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
        )
    ):
        return URL.create(
            drivername="postgresql+psycopg",
            username=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=5432,
            database=os.environ["POSTGRES_DB"],
        )

    # Fallback for existing configurations
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "Database connection environment variables are missing"
        )

    return database_url


engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"connect_timeout": 5},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
