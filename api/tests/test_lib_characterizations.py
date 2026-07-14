"""Characterization listing tests — Constitution Principle II/III.

Characterizations must always be displayed in the category's configured feature
order: `GET /api/characterizations/` sorts, within each asset, by the matching
`specifications.sort_order` (feature code as tiebreaker; features without a spec
row go last). This is what makes the Review page / asset detail render the same
order as the Propose/Modify forms (which build from the specs endpoint).
"""

from types import SimpleNamespace

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal.models import Asset, Characterization
from app.taxo.internal.models import Category, Specification


def _superuser(uid=1):
    return SimpleNamespace(id=uid, username="su", profile="ADMINISTRATOR",
                           is_superuser=True, is_active=True)


def _seed_asset_with_chars(session):
    session.add(Category(code="PROMPTS", name="Prompts"))
    # sort_order deliberately disagrees with alphabetical order.
    session.add(Specification(category="PROMPTS", feature="ZZZ_FIRST", sort_order=10))
    session.add(Specification(category="PROMPTS", feature="MMM_SECOND", sort_order=20))
    session.add(Specification(category="PROMPTS", feature="AAA_THIRD", sort_order=30))
    asset = Asset(name="My Prompt", status="PUBLISHED", category="PROMPTS")
    session.add(asset)
    session.commit()
    session.refresh(asset)
    # Insert chars alphabetically (worst case) + one feature with NO spec row.
    for feature in ("AAA_THIRD", "BBB_NO_SPEC", "MMM_SECOND", "ZZZ_FIRST"):
        session.add(Characterization(asset=asset.id, feature=feature, value="v"))
    session.commit()
    return asset


def test_characterizations_follow_spec_sort_order(session, client):
    """Rows come back in spec sort_order, with spec-less features last."""
    asset = _seed_asset_with_chars(session)
    app.dependency_overrides[current_active_user] = _superuser
    try:
        r = client.get("/api/characterizations/")
    finally:
        app.dependency_overrides.pop(current_active_user, None)

    assert r.status_code == 200
    features = [row["feature"] for row in r.json()["data"] if row["asset"] == asset.id]
    assert features == ["ZZZ_FIRST", "MMM_SECOND", "AAA_THIRD", "BBB_NO_SPEC"]
