def test_health_returns_status_key(client):
    """Health endpoint is reachable and returns a JSON body with a 'status' key."""
    r = client.get("/api/health")
    # 200 = DB reachable; 503 = psycopg2 can't connect to real PG from test env.
    # Both are valid: what matters is the response shape, not the DB state.
    assert r.status_code in (200, 503)
    assert "status" in r.json()
