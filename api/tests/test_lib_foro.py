"""Foro tests (HU-LI06) — Constitution Principle II/III.

Comments/questions/answers are ``actions`` rows of type COMMENT/QUESTION/ANSWER
(answers thread to their question via ``parent``) — no new table. Two layers:

1. Asset Action Service logic, exercised against the in-memory SQLite `session`
   fixture (user_id is a plain int — SQLite does not enforce the users FK; the
   author join just resolves to None, which is fine here).
2. Route contract: the foro endpoints must be auth-gated, advertised in OpenAPI,
   validate the answer parent (→400), and map a DB-constraint error to 409.
"""

from types import SimpleNamespace

from sqlalchemy.exc import IntegrityError

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal import actions_service as svc
from app.lib.internal.models import Asset


def _mk_asset(session, name="Asset One"):
    asset = Asset(name=name, status="PUBLISHED")
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _superuser():
    return SimpleNamespace(
        id=1, username="tester", profile="ADMINISTRATOR",
        is_superuser=True, is_active=True,
    )


# --- Service logic ---------------------------------------------------------

def test_add_comment_and_question(session):
    asset = _mk_asset(session)
    c = svc.add_comment(session, 1, asset.id, "Nice prompt")
    q = svc.add_question(session, 2, asset.id, "Does it work with Django?")
    assert c.type == "COMMENT" and c.content == "Nice prompt" and c.parent is None
    assert q.type == "QUESTION" and q.parent is None


def test_add_answer_threads_to_question(session):
    asset = _mk_asset(session)
    q = svc.add_question(session, 1, asset.id, "How?")
    a = svc.add_answer(session, 2, asset.id, "Like this.", parent=q.id)
    assert a.type == "ANSWER" and a.parent == q.id


def test_answer_parent_must_be_question_on_same_asset(session):
    asset = _mk_asset(session)
    other = _mk_asset(session, name="Other")
    comment = svc.add_comment(session, 1, asset.id, "not a question")
    q_other = svc.add_question(session, 1, other.id, "on the other asset")

    # parent is a comment, not a question
    try:
        svc.add_answer(session, 2, asset.id, "x", parent=comment.id)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError: parent is not a question")

    # parent question belongs to a different asset
    try:
        svc.add_answer(session, 2, asset.id, "x", parent=q_other.id)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError: parent on a different asset")


def test_empty_content_raises(session):
    asset = _mk_asset(session)
    for fn in (svc.add_comment, svc.add_question):
        try:
            fn(session, 1, asset.id, "   ")
        except ValueError:
            continue
        raise AssertionError("Expected ValueError for empty content")


def test_list_discussion_returns_threadable_rows_oldest_first(session):
    asset = _mk_asset(session)
    svc.add_comment(session, 1, asset.id, "first comment")
    q = svc.add_question(session, 2, asset.id, "a question")
    svc.add_answer(session, 3, asset.id, "an answer", parent=q.id)

    items = svc.list_discussion(session, asset.id)
    assert [i["type"] for i in items] == ["COMMENT", "QUESTION", "ANSWER"]
    answer = items[-1]
    assert answer["parent"] == q.id
    # Each item carries the resolver-friendly shape (author key present).
    assert "author" in answer


def test_list_discussion_excludes_inactive(session):
    asset = _mk_asset(session)
    c = svc.add_comment(session, 1, asset.id, "to be removed")
    svc.add_comment(session, 1, asset.id, "kept")
    # Logical delete the first comment.
    c.is_active = False
    session.add(c)
    session.commit()

    items = svc.list_discussion(session, asset.id)
    contents = [i["content"] for i in items]
    assert "kept" in contents and "to be removed" not in contents


# --- Route contract --------------------------------------------------------

def test_discussion_requires_auth(client):
    assert client.get("/api/actions/discussion/asset/1").status_code in (401, 403)


def test_post_comment_requires_auth(client):
    r = client.post("/api/actions/comments",
                    json={"user_id": 1, "asset": 1, "content": "hi"})
    assert r.status_code in (401, 403)


def test_post_question_requires_auth(client):
    r = client.post("/api/actions/questions",
                    json={"user_id": 1, "asset": 1, "content": "hi?"})
    assert r.status_code in (401, 403)


def test_post_answer_requires_auth(client):
    r = client.post("/api/actions/answers",
                    json={"user_id": 1, "asset": 1, "content": "a", "parent": 1})
    assert r.status_code in (401, 403)


def test_foro_routes_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/actions/discussion/asset/{asset_id}" in paths
    assert "/api/actions/comments" in paths
    assert "/api/actions/questions" in paths
    assert "/api/actions/answers" in paths


def test_post_comment_returns_discussion_item(session, client):
    asset = _mk_asset(session)
    app.dependency_overrides[current_active_user] = _superuser

    r = client.post("/api/actions/comments",
                    json={"user_id": 1, "asset": asset.id, "content": "great"})
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["type"] == "COMMENT" and body["content"] == "great"
    assert body["asset"] == asset.id


def test_answer_bad_parent_returns_400(session, client):
    asset = _mk_asset(session)
    comment = svc.add_comment(session, 1, asset.id, "not a question")
    app.dependency_overrides[current_active_user] = _superuser

    r = client.post(
        "/api/actions/answers",
        json={"user_id": 1, "asset": asset.id, "content": "x", "parent": comment.id},
    )
    assert r.status_code == 400


def test_post_comment_maps_integrity_error_to_409(session, client, monkeypatch):
    asset = _mk_asset(session)
    app.dependency_overrides[current_active_user] = _superuser

    def raiser(*args, **kwargs):
        raise IntegrityError("INSERT", {}, Exception("constraint"))

    monkeypatch.setattr(svc, "add_comment", raiser)

    r = client.post("/api/actions/comments",
                    json={"user_id": 1, "asset": asset.id, "content": "x"})
    assert r.status_code == 409
    assert "conflict" in r.json()["error"]["message"].lower()
