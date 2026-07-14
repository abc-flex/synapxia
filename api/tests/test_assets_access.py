"""Contract/permission tests for GET /api/assets/with-access (Constitution III).

The route's access summary is now computed Python-side (the old Postgres-only
array_agg/bool_or aggregate was replaced when the listing became caller-scoped,
HU-LI08), so its behavior runs on the SQLite test DB — see
test_lib_access_enforcement.py for the visibility/my_access coverage. Here we
lock down the security gate: the endpoint must require authentication like its
sibling `GET /api/assets/`.
"""


def test_with_access_requires_auth(client):
    """Unauthenticated request must be rejected (401/403), never reach the handler."""
    r = client.get("/api/assets/with-access")
    assert r.status_code in (401, 403)


def test_with_access_accepts_pagination_params(client):
    """skip/limit are accepted by the route (still gated → auth error, not 404/422)."""
    r = client.get("/api/assets/with-access?skip=0&limit=10")
    assert r.status_code in (401, 403)


def test_plain_assets_list_still_gated(client):
    """Sibling GET /api/assets/ contract is unchanged (still auth-gated)."""
    r = client.get("/api/assets/")
    assert r.status_code in (401, 403)
