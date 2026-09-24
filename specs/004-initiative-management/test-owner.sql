-- Initiative Management (004) — test owner for validating per-initiative access.
--
-- NOT part of the seed (db/sql/): run it by hand on a local/dev database when you
-- want to exercise quickstart.md as a non-superuser. `felipe.cardenas` is already
-- ADMINISTRATIVE in the seed (db/sql/32-collab-insert.sql); this script only gives
-- him grants on some initiatives but not others:
--
--   init 1 (IN_PROGRESS) MANAGE · init 3 (ACCEPTED) MANAGE · init 2 (DELIVERED) VIEW
--   inits 4–5: no grant (hidden from his list, 403 on direct reads)
--
-- Idempotent. Undo: see the bottom of this file.
--
--   docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
--     < specs/004-initiative-management/test-owner.sql
BEGIN;

INSERT INTO init_permissions (init, target_type, target_code, access_level)
SELECT g.init, 'USER', u.id::text, g.access_level
FROM (VALUES (1, 'MANAGE'), (3, 'MANAGE'), (2, 'VIEW')) AS g(init, access_level)
JOIN users u ON u.username = 'felipe.cardenas'
WHERE NOT EXISTS (
    SELECT 1 FROM init_permissions p
    WHERE p.init = g.init AND p.target_type = 'USER' AND p.target_code = u.id::text
      AND p.access_level = g.access_level AND (p.valid_to IS NULL OR p.valid_to > NOW())
);

COMMIT;

-- Undo (revokes the grants — grants are never deleted):
-- UPDATE init_permissions SET valid_to = NOW()
--  WHERE target_type = 'USER' AND valid_to IS NULL
--    AND target_code = (SELECT id::text FROM users WHERE username = 'felipe.cardenas');
