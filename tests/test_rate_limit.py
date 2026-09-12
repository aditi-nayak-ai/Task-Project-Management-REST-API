import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def rate_limited_client(db_session):
    """
    Deliberately does NOT disable the limiter (unlike the `client` fixture
    in conftest.py), so this is the one place the 5/minute cap on
    /auth/login is actually exercised.
    """
    from app.main import app
    from app.db.session import get_db
    from app.core.limiter import limiter

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    limiter.enabled = True  # other test modules disable this globally; restore it here
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    limiter.enabled = False


def test_login_is_rate_limited_after_five_attempts_per_minute(rate_limited_client):
    rate_limited_client.post("/auth/register", json={"email": "rl@test.com", "password": "Passw0rd1!"})

    statuses = []
    for _ in range(6):
        r = rate_limited_client.post(
            "/auth/login", data={"username": "rl@test.com", "password": "wrong-password"}
        )
        statuses.append(r.status_code)

    # First 5 are rejected as bad credentials (401); the 6th within the
    # same minute must be rate-limited (429), not just another 401.
    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429
