-- Dashboard Management (specs/006-dashboard-management) — TEST DATA, NOT SEED DATA.
--
-- Gives the seeded non-superuser analyst `felipe.cardenas` (profile ADMINISTRATIVE,
-- which holds ANA/DASHBOARDS with edit rights) grants to exercise the quickstart:
--   dashboard 1 → MANAGE   (editable)
--   dashboard 2 → VIEW     (read-only)
--   dashboard 3 → VIEW     (already, through the seed's PUBLIC grant)
--
-- The seed grants dashboards 1 and 3 to PUBLIC/VIEW, so every user can SEE them.
-- For the "hidden" case, create a dashboard as admin and revoke its creator grant.
-- Run by hand: docker compose exec -T db psql -U postgres -d synapxia -f - < this file

INSERT INTO dashboard_permissions (dashboard, target_type, target_code, access_level)
SELECT 1, 'USER', CAST(u.id AS VARCHAR), 'MANAGE' FROM users u WHERE u.username = 'felipe.cardenas';

INSERT INTO dashboard_permissions (dashboard, target_type, target_code, access_level)
SELECT 2, 'USER', CAST(u.id AS VARCHAR), 'VIEW' FROM users u WHERE u.username = 'felipe.cardenas';

-- ── Cleanup (run after testing): revoke the grants above — never delete them ──
-- UPDATE dashboard_permissions dp SET valid_to = NOW()
-- FROM users u
-- WHERE u.username = 'felipe.cardenas'
--   AND dp.target_type = 'USER' AND dp.target_code = CAST(u.id AS VARCHAR)
--   AND dp.dashboard IN (1, 2) AND dp.valid_to IS NULL;
