"""Auth contract tests — covers Constitution Principle II (contract stability)."""


def test_login_missing_credentials_returns_422(client):
    """Empty POST to login must return 422 (missing required form fields)."""
    r = client.post("/api/auth/login", data={})
    assert r.status_code == 422


def test_login_wrong_password_returns_400(client):
    """Non-existent user / wrong password returns fastapi-users' 400
    LOGIN_BAD_CREDENTIALS (not 401, not 500) — the contract the UI reads."""
    r = client.post(
        "/api/auth/login",
        data={"username": "no-such-user@example.com", "password": "wrongpassword"},
    )
    assert r.status_code == 400


def test_me_without_token_returns_401(client):
    """GET /api/auth/me without a bearer token must return 401."""
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_invalid_token_returns_401(client):
    """GET /api/auth/me with a malformed token must return 401, not 500."""
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert r.status_code == 401


def test_login_response_shape_on_failure(client):
    """A failed login keeps fastapi-users' native shape: {"detail": "LOGIN_BAD_CREDENTIALS"}
    (auth routes are outside the {data, error, meta} envelope)."""
    r = client.post(
        "/api/auth/login",
        data={"username": "ghost@example.com", "password": "nope"},
    )
    assert r.status_code == 400
    assert r.json() == {"detail": "LOGIN_BAD_CREDENTIALS"}


def test_cookie_login_failure_has_the_same_contract(client):
    """The UI logs in through /api/auth/cookie/login; it must fail the same way."""
    r = client.post(
        "/api/auth/cookie/login",
        data={"username": "ghost@example.com", "password": "nope"},
    )
    assert r.status_code == 400
    assert r.json() == {"detail": "LOGIN_BAD_CREDENTIALS"}
