"""Fixtures shared by every test file: no network, a throwaway database, one lesson."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings
from app.models import TeachingSession, User


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests never call a provider, whatever is in the local .env."""
    monkeypatch.setattr(settings, "stt_provider", "fake")
    monkeypatch.setattr(settings, "llm_provider", "fake")


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
