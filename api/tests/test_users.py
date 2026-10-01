"""User CRUD contract tests — covers Constitution Principle II (contract stability)
and the PR #25 auth gate (every endpoint needs a token; ADMIN/USERS for reads)."""
from tests.inits_helpers import override, superuser, user


def test_users_endpoints_require_a_token(client):
    """Without a bearer token every users endpoint answers 401."""
    for path in ("/api/users/", "/api/users/select", "/api/users/99999"):
        assert client.get(path).status_code == 401, path


def test_list_users_returns_list(client):
    """GET /api/users/ must return a JSON array (empty on fresh SQLite DB)."""
    override(superuser())
    r = client.get("/api/users/")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


def test_list_users_pagination_params_accepted(client):
    """List endpoint must accept skip + limit query params without error."""
    override(superuser())
    r = client.get("/api/users/?skip=0&limit=10")
    assert r.status_code == 200


def test_list_users_select_returns_list(client):
    """GET /api/users/select must return a JSON array for dropdown consumers."""
    override(superuser())
    r = client.get("/api/users/select")
    assert r.status_code == 200
    assert isinstance(r.json()["data"], list)


def test_list_users_select_needs_no_admin_privilege(client):
    """The dropdown endpoint only needs an active user, not ADMIN/USERS."""
    override(user(1, profile="COLLABORATOR"))
    assert client.get("/api/users/select").status_code == 200


def test_list_users_needs_admin_users_privilege(client):
    """A user without the ADMIN/USERS privilege cannot list users."""
    override(user(1, profile="COLLABORATOR"))
    assert client.get("/api/users/").status_code == 403


def test_get_nonexistent_user_returns_404(client):
    """GET /api/users/99999 on an empty DB must return 404, not 500."""
    override(superuser())
    r = client.get("/api/users/99999")
    assert r.status_code == 404
