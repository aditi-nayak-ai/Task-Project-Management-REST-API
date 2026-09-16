import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-characters-long"
os.environ["RUN_MIGRATIONS_ON_STARTUP"] = "false"  # we build schema directly, not via alembic, for test speed

import pytest
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db.base import Base
from app.models import user, project, task, refresh_token, project_manager, audit_log  # noqa: F401 -- registers models on Base.metadata
from app.core.security import hash_password
from app.models.user import User, UserRole


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    import app.db.session as db_session_module
    db_session_module.engine = engine
    db_session_module.SessionLocal = TestingSessionLocal

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        try:
            session.close()
        except Exception:
            pass  # engine may already be disposed by the app's own shutdown hook


@pytest.fixture()
def client(db_session):
    from app.main import app
    from app.db.session import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # fixture owns closing the session, not the dependency

    app.dependency_overrides[get_db] = override_get_db

    from app.core.limiter import limiter
    limiter.enabled = False  # rate limiting is tested separately in test_rate_limit.py

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(db_session, email: str, password: str, role: UserRole) -> User:
    u = User(email=email, hashed_password=hash_password(password), role=role, is_active=True)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture()
def admin_user(db_session):
    return make_user(db_session, "admin@test.com", "AdminPass1!", UserRole.admin)


@pytest.fixture()
def manager_user(db_session):
    return make_user(db_session, "manager@test.com", "ManagerPass1!", UserRole.manager)


@pytest.fixture()
def regular_user(db_session):
    return make_user(db_session, "user@test.com", "UserPass1!", UserRole.user)


def auth_header(client, email: str, password: str) -> dict:
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
