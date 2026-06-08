import os

# Must be set before any app module is imported, because settings = Settings()
# is evaluated at import time and requires these environment variables.
os.environ.setdefault("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com/")
os.environ.setdefault("AZURE_OPENAI_API_KEY", "test-key-for-unit-tests-only")
os.environ.setdefault("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini")
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, TriageRecord
from app.db.session import get_db
from app.schemas.triage import TriageResponse

# StaticPool forces every engine.connect() call to reuse the same underlying
# connection, which is required for SQLite in-memory databases to be shared
# across the session and the TestClient's dependency-injected session.
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(TEST_ENGINE)

TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture
def db_session():
    session = TestingSession()
    yield session
    session.close()
    # Wipe all rows between tests so state does not bleed across test functions.
    with TEST_ENGINE.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture
def client(db_session):
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session

    # Prevent the lifespan from running create_tables() against the real DB.
    with patch("app.db.init_db.create_tables"):
        with TestClient(app) as c:
            yield c


@pytest.fixture
def sample_triage_response():
    return TriageResponse(
        category="Refund Request",
        urgency="Low",
        urgency_reason="Customer submitted a refund request for a recent purchase.",
        sentiment="Negative",
        suggested_owner="Billing Team",
        draft_response="Thank you for contacting us. We will review your refund request promptly.",
        confidence="High",
        abusive_flag=False,
    )
