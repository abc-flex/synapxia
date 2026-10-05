-- Dashboard Catalog (specs/007-dashboard-catalog) — TEST DATA, NOT SEED DATA.
--
-- Sets up every case the quickstart exercises:
--   * dashboard 2 "by Role": its `role` parameter is bound to the seed grant ROLE TL.
--     adriana.velez (COLLABORATOR, role TL) reaches it through that grant → role = TL, fixed.
--     santiago.marin (REVIEWER, FRONT/ALPHA) gets a USER grant → reaches it another way →
--     `role` is asked for (free input; no list).
--   * "Catalog Test — Internal Page": PUBLISHED, INTERNAL_PAGE (/support), PUBLIC/VIEW,
--     with a LIST parameter (LANGUAGE), a required NUMBER without default and a BOOLEAN.
--   * "Catalog Test — Draft": DRAFT with a PUBLIC grant → must never appear in the catalog.
--
-- Run by hand: docker compose exec -T db psql -U postgres -d synapxia -f - < this file

-- Bind dashboard 2's `role` parameter to its ROLE TL grant.
UPDATE parameters p SET context_binding = dp.id, updated_at = NOW()
FROM dashboard_permissions dp
WHERE p.dashboard = 2 AND p.name = 'role'
  AND dp.dashboard = 2 AND dp.target_type = 'ROLE' AND dp.target_code = 'TL'
  AND dp.valid_to IS NULL;

-- santiago.marin reaches dashboard 2 through a USER grant (not the bound one).
INSERT INTO dashboard_permissions (dashboard, target_type, target_code, access_level)
SELECT 2, 'USER', CAST(u.id AS VARCHAR), 'VIEW' FROM users u WHERE u.username = 'santiago.marin';

-- Internal Page test dashboard.
WITH d AS (
    INSERT INTO dashboards (name, description, type, sources_types, source_url, status, tags, detail)
    VALUES ('Catalog Test — Internal Page',
            'Internal page used to verify the viewer, its load tracking and timeouts.',
            'REPORT', 'INTERNAL_PAGE', '/support', 'PUBLISHED',
            '["test", "catalog"]', '# Catalog test\nOpens `/support` in the viewer.')
    RETURNING id
), g AS (
    INSERT INTO dashboard_permissions (dashboard, target_type, target_code, access_level)
    SELECT id, 'PUBLIC', 'ALL', 'VIEW' FROM d
    RETURNING dashboard
)
INSERT INTO parameters (dashboard, name, label, data_type, default_value, is_required, list)
SELECT dashboard, v.name, v.label, v.data_type, v.default_value, v.is_required, v.list
FROM g, (VALUES
    ('language',  'Language',   'STRING',  'PYTHON', TRUE,  'LANGUAGE'),
    ('top_n',     'Top N',      'NUMBER',  NULL,     TRUE,  NULL),
    ('only_mine', 'Only mine',  'BOOLEAN', NULL,     FALSE, NULL)
) AS v(name, label, data_type, default_value, is_required, list);

-- Draft test dashboard (hidden from the catalog despite its PUBLIC grant).
WITH d AS (
    INSERT INTO dashboards (name, description, type, sources_types, source_url, status, tags)
    VALUES ('Catalog Test — Draft', 'Must never appear in the catalog.',
            'DASHBOARD', 'POWER_BI', 'https://app.powerbi.com/view?r=catalog-test-draft',
            'DRAFT', '["test"]')
    RETURNING id
)
INSERT INTO dashboard_permissions (dashboard, target_type, target_code, access_level)
SELECT id, 'PUBLIC', 'ALL', 'VIEW' FROM d;

-- ── Cleanup (run after testing) ─────────────────────────────────────────────
-- UPDATE parameters SET context_binding = NULL WHERE dashboard = 2 AND name = 'role';
-- UPDATE dashboard_permissions dp SET valid_to = NOW() FROM users u
--  WHERE u.username = 'santiago.marin' AND dp.dashboard = 2
--    AND dp.target_type = 'USER' AND dp.target_code = CAST(u.id AS VARCHAR) AND dp.valid_to IS NULL;
-- UPDATE dashboards SET is_active = FALSE WHERE name LIKE 'Catalog Test — %';
-- Execution rows are append-only by design; test rows stay (they are labelled by dashboard/user).
