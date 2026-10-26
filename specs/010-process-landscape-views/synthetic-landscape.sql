-- Synthetic process landscape for the SC-003 scale check
-- (specs/010-process-landscape-views, quickstart §4). DEVELOPMENT ONLY, never seed.
--
-- Writes only process rows and their links: `processes`, `related_processes`,
-- `process_assets`, `process_inits`. Owners, units, assets and initiatives are
-- EXISTING rows; nothing is added to any other table. Every code starts with
-- `SYN-`; synthetic-landscape-remove.sql deletes exactly those rows.
-- Deterministic: running it twice changes nothing (ON CONFLICT DO NOTHING).
--
-- Shape: 12 primary + 8 support top-level processes, 5 children each, 2
-- grandchildren per child = 320 processes; ~600 relations over all seven
-- types (respecting the SUPPORTS / PRECEDES rules); links to existing active
-- assets / initiatives on about a third of the processes.

BEGIN;

CREATE TEMP TABLE syn_tops ON COMMIT DROP AS
SELECT 'SYN-' || t || lpad(i::text, 2, '0') AS code,
       CASE t WHEN 'P' THEN 'PRIMARY' ELSE 'SUPPORT' END AS type,
       i, t
FROM (SELECT 'P' AS t, generate_series(1, 12) AS i
      UNION ALL SELECT 'S', generate_series(1, 8)) s;

CREATE TEMP TABLE syn_units ON COMMIT DROP AS
SELECT code, row_number() OVER (ORDER BY code) - 1 AS n
FROM business_units WHERE is_active;

CREATE TEMP TABLE syn_owner ON COMMIT DROP AS
SELECT min(id) AS id FROM users WHERE is_active;

-- ── Processes ───────────────────────────────────────────────────────────────
INSERT INTO processes (code, name, description, type, parent, unit, owner, status)
SELECT p.code, p.name, 'Synthetic process for the landscape scale check.', p.type, p.parent,
       (SELECT code FROM syn_units WHERE n = p.k % GREATEST((SELECT count(*) FROM syn_units), 1)),
       (SELECT id FROM syn_owner),
       CASE WHEN p.k % 17 = 0 THEN 'DRAFT' WHEN p.k % 23 = 0 THEN 'REVIEW' ELSE 'PUBLISHED' END
FROM (
  SELECT code, 'Synthetic ' || code AS name, type, NULL::varchar AS parent, i * 7 AS k FROM syn_tops
  UNION ALL
  SELECT t.code || '-C' || c, 'Synthetic ' || t.code || ' step ' || c, t.type, t.code, t.i * 7 + c
  FROM syn_tops t, generate_series(1, 5) c
  UNION ALL
  SELECT t.code || '-C' || c || '-G' || g, 'Synthetic ' || t.code || ' step ' || c || '.' || g,
         t.type, t.code || '-C' || c, t.i * 13 + c * 3 + g
  FROM syn_tops t, generate_series(1, 5) c, generate_series(1, 2) g
) p
ON CONFLICT (code) DO NOTHING;

CREATE TEMP TABLE syn_all ON COMMIT DROP AS
SELECT code, type, row_number() OVER (ORDER BY code) AS n
FROM processes WHERE code LIKE 'SYN-%';

-- ── Relations ───────────────────────────────────────────────────────────────
-- The primary chain (PRECEDES, same type).
INSERT INTO related_processes (source, target, type, rationale)
SELECT a.code, b.code, 'PRECEDES', 'Synthetic chain.'
FROM syn_tops a JOIN syn_tops b ON a.t = 'P' AND b.t = 'P' AND b.i = a.i + 1
ON CONFLICT DO NOTHING;

-- Each support activity supports three primary ones (SUPPORTS: Support → Primary).
INSERT INTO related_processes (source, target, type, rationale)
SELECT s.code, p.code, 'SUPPORTS', 'Synthetic support.'
FROM syn_tops s JOIN syn_tops p ON s.t = 'S' AND p.t = 'P'
 AND p.i IN ((s.i % 12) + 1, ((s.i + 4) % 12) + 1, ((s.i + 8) % 12) + 1)
ON CONFLICT DO NOTHING;

-- Children of the same parent in sequence (PRECEDES, same type).
INSERT INTO related_processes (source, target, type, rationale)
SELECT t.code || '-C' || c, t.code || '-C' || (c + 1), 'PRECEDES', 'Synthetic sub-process flow.'
FROM syn_tops t, generate_series(1, 4) c
ON CONFLICT DO NOTHING;

-- The rest: type-free relation types between scattered processes.
INSERT INTO related_processes (source, target, type, rationale)
SELECT a.code, b.code, x.type, 'Synthetic relation.'
FROM generate_series(1, 540) k
CROSS JOIN LATERAL (SELECT (ARRAY['TRIGGERS','CALLS','FEEDS_INTO','INTERACTS_WITH','GOVERNS'])[k % 5 + 1] AS type) x
JOIN syn_all a ON a.n = (k * 37) % 320 + 1
JOIN syn_all b ON b.n = (k * 91 + (k / 320) * 53 + 11) % 320 + 1
WHERE a.code <> b.code AND (x.type <> 'INTERACTS_WITH' OR a.code < b.code)
ON CONFLICT DO NOTHING;

-- ── Links to existing assets / initiatives ──────────────────────────────────
INSERT INTO process_assets (process, asset, type, rationale)
SELECT p.code, a.id, 'RELATED_TO', 'Synthetic link.'
FROM syn_all p
JOIN (SELECT id, row_number() OVER (ORDER BY id) - 1 AS n FROM assets WHERE is_active) a
  ON a.n = p.n % GREATEST((SELECT count(*) FROM assets WHERE is_active), 1)
WHERE p.n % 3 = 0
ON CONFLICT DO NOTHING;

INSERT INTO process_inits (process, init, type, rationale)
SELECT p.code, i.id, 'RELATED_TO', 'Synthetic link.'
FROM syn_all p
JOIN (SELECT id, row_number() OVER (ORDER BY id) - 1 AS n FROM initiatives WHERE is_active) i
  ON i.n = p.n % GREATEST((SELECT count(*) FROM initiatives WHERE is_active), 1)
WHERE p.n % 4 = 1
ON CONFLICT DO NOTHING;

COMMIT;

SELECT (SELECT count(*) FROM processes WHERE code LIKE 'SYN-%') AS processes,
       (SELECT count(*) FROM related_processes WHERE source LIKE 'SYN-%') AS relations,
       (SELECT count(*) FROM process_assets WHERE process LIKE 'SYN-%') AS asset_links,
       (SELECT count(*) FROM process_inits WHERE process LIKE 'SYN-%') AS init_links;
