"""Test setup.

By default tests run on an in-memory SQLite database (no setup needed).
To run them against real PostgreSQL instead, create an EMPTY database and set:
    TEST_DATABASE_URL=postgresql+psycopg://studyos:studyos@localhost:5432/studyos_test
"""
import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import get_now
from app.main import app

# Wednesday 4 March 2026, 10:00 UTC. Frozen so "today"/"overdue" are deterministic.
NOW = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
TEST_URL = os.environ.get("TEST_DATABASE_URL", "sqlite://")


@pytest.fixture()
def engine():
    if TEST_URL.startswith("sqlite"):
        eng = create_engine(TEST_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(eng, "connect")
        def _fk_on(dbapi_conn, _):  # SQLite ignores foreign keys unless asked
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    else:
        eng = create_engine(TEST_URL)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def make_client(engine):
    """Factory: each call returns a separate browser (own cookie jar)."""
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_now] = lambda: NOW
    clients = []

    def factory() -> TestClient:
        c = TestClient(app)
        clients.append(c)
        return c

    yield factory
    app.dependency_overrides.clear()


def register(client: TestClient, email="alice@example.com", name="Alice", tz="UTC"):
    r = client.post("/api/auth/register", json={"email": email, "name": name,
                                                "password": "correct-horse-1", "timezone": tz})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def client(make_client):
    c = make_client()
    register(c)
    return c


@pytest.fixture()
def other(make_client, client):
    c = make_client()
    register(c, email="bob@example.com", name="Bob")
    return c


@pytest.fixture()
def subject(client):
    r = client.post("/api/subjects", json={"name": "Operating Systems", "color": "#3366ff"})
    assert r.status_code == 201
    return r.json()
