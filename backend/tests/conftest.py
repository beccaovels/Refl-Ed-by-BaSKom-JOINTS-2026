"""Fixtures shared by every test file: no network, a throwaway database, one lesson."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.models import TeachingSession, User
from app.services import llm


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests never call a provider, whatever is in the local .env."""
    monkeypatch.setattr(settings, "stt_provider", "fake")
    monkeypatch.setattr(settings, "llm_provider", "fake")
    llm._resting_until.clear()  # no test inherits another test's failed model


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def lesson(db):
    user = User(name="Bu Rina", email="rina@example.com")
    db.add(user)
    db.commit()
    session = TeachingSession(
        user_id=user.id, profile_id="matematika-fase-e", class_name="X-1", subject="Matematika", chapter="Fungsi kuadrat"
    )
    db.add(session)
    db.commit()
    return session


# --- API tests: the app on a throwaway database, through FastAPI's TestClient ---


@pytest.fixture
def engine():
    # one shared connection: background report jobs run on another thread than the request
    from sqlalchemy.pool import StaticPool

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def client(engine, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from app.api import reports
    from app.core.db import get_session
    from app.main import app

    def override():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    app.dependency_overrides[get_session] = override
    reports._jobs.clear()
    yield TestClient(app)  # not a context manager, so startup does not touch data/app.db
    app.dependency_overrides.clear()
    reports._jobs.clear()


@pytest.fixture
def login(client):
    """Log a teacher in and return the headers for their requests."""

    def _login(name="Bu Rina", email="rina@example.com"):
        user = client.post("/api/auth/login", json={"name": name, "email": email}).json()
        return {"X-User-Id": user["id"]}

    return _login
