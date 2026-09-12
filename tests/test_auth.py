def test_register_then_login_returns_token_pair(client):
    r = client.post("/auth/register", json={"email": "new@test.com", "password": "Passw0rd1!"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "new@test.com"
    assert body["role"] == "user"

    r = client.post("/auth/login", data={"username": "new@test.com", "password": "Passw0rd1!"})
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


def test_duplicate_registration_returns_400_not_500(client):
    client.post("/auth/register", json={"email": "dup@test.com", "password": "Passw0rd1!"})
    r = client.post("/auth/register", json={"email": "dup@test.com", "password": "Passw0rd1!"})
    assert r.status_code == 400


def test_login_wrong_password_returns_401(client):
    client.post("/auth/register", json={"email": "wp@test.com", "password": "Correct1!"})
    r = client.post("/auth/login", data={"username": "wp@test.com", "password": "Wrong1!"})
    assert r.status_code == 401


def test_login_nonexistent_user_returns_401_same_as_wrong_password(client):
    r = client.post("/auth/login", data={"username": "nobody@test.com", "password": "whatever"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials"


def test_refresh_token_issues_new_access_token(client):
    client.post("/auth/register", json={"email": "refresh@test.com", "password": "Passw0rd1!"})
    login = client.post("/auth/login", data={"username": "refresh@test.com", "password": "Passw0rd1!"})
    refresh_token = login.json()["refresh_token"]

    r = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_refresh_with_garbage_token_returns_401(client):
    r = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert r.status_code == 401


def test_logout_revokes_refresh_token(client):
    client.post("/auth/register", json={"email": "logout@test.com", "password": "Passw0rd1!"})
    login = client.post("/auth/login", data={"username": "logout@test.com", "password": "Passw0rd1!"})
    refresh_token = login.json()["refresh_token"]

    r = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert r.status_code == 204

    # the same refresh token must no longer work after logout
    r = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 401


def test_protected_endpoint_rejects_missing_token(client):
    r = client.get("/users/me")
    assert r.status_code == 401


def test_protected_endpoint_rejects_garbage_token(client):
    r = client.get("/users/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401
