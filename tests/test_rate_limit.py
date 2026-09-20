import pytest
from fastapi.testclient import TestClient
 
# Must match the @limiter.limit(...) on /auth/login in app/api/auth.py.
LOGIN_LIMIT_PER_MINUTE = 30
 
 
@pytest.fixture()
def rate_limited_client(db_session):
    """
    Deliberately does NOT disable the limiter (unlike the `client` fixture
    in conftest.py), so this is the one place the per-minute cap on
    /auth/login is actually exercised.
    """
    from app.main import app
    from app.db.session import get_db
    from app.core.limiter import limiter
 
    def override_get_db():
        yield db_session
 
    app.dependency_overrides[get_db] = override_get_db
    limiter.enabled = True  # other test modules disable this globally; restore it here
    limiter.reset()  # start every test with empty rate-limit counters
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    limiter.reset()
    limiter.enabled = False
 
 
def test_login_is_rate_limited_after_limit_per_minute(rate_limited_client):
    # An unknown email is enough: the endpoint answers 401 without running a
    # bcrypt check, so 31 attempts stay fast, and the limiter counts every
    # attempt regardless of whether the credentials were valid.
    statuses = []
    for _ in range(LOGIN_LIMIT_PER_MINUTE + 1):
        r = rate_limited_client.post(
            "/auth/login", data={"username": "nobody@test.com", "password": "wrong-password"}
        )
        statuses.append(r.status_code)
 
    # The first LOGIN_LIMIT_PER_MINUTE attempts are rejected as bad credentials
    # (401); the next one within the same minute must be rate-limited (429).
    assert statuses[:LOGIN_LIMIT_PER_MINUTE] == [401] * LOGIN_LIMIT_PER_MINUTE
    assert statuses[LOGIN_LIMIT_PER_MINUTE] == 429
