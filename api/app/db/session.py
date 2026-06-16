from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings


def _database_url():
    if settings.POSTGRES_HOST and settings.POSTGRES_PASSWORD:
        return URL.create(
            "postgresql+psycopg2",
            username=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            query={"sslmode": "require"},
        )

    if settings.DATABASE_URL:
        return settings.DATABASE_URL

    raise RuntimeError(
        "PostgreSQL is not configured. Set POSTGRES_HOST and POSTGRES_PASSWORD "
        "or set DATABASE_URL to a PostgreSQL connection string."
    )


database_url = _database_url()
connect_args = {}
database_url_text = str(database_url)

if database_url_text.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    sqlite_path = make_url(database_url_text).database
    if sqlite_path and sqlite_path != ":memory:":
        Path(sqlite_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
elif database_url_text.startswith("postgresql") and "sslmode=" not in database_url_text:
    connect_args["sslmode"] = "require"

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
