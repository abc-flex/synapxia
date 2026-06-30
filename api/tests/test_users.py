"""User CRUD contract tests — covers Constitution Principle II (contract stability)."""


def test_list_users_returns_list(client):
    """GET /api/users/ must return a JSON array (empty on fresh SQLite DB)."""
    r = client.get("/api/users/")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


def test_list_users_pagination_params_accepted(client):
    """List endpoint must accept skip + limit query params without error."""
    r = client.get("/api/users/?skip=0&limit=10")
    assert r.status_code == 200


def test_list_users_select_returns_list(client):
    """GET /api/users/select must return a JSON array for dropdown consumers."""
    r = client.get("/api/users/select")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


def test_get_nonexistent_user_returns_404(client):
    """GET /api/users/99999 on an empty DB must return 404, not 500."""
    r = client.get("/api/users/99999")
    assert r.status_code == 404
