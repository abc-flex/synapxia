-- =============================================================================
-- Synthetic usage data for SpecKit 008 (Usage Metrics, FR-019). DEVELOPMENT ONLY.
--
-- Writes ONLY to `executions`. No user, dashboard, grant, parameter or assignment
-- is created or changed: the runs are spread over the dashboards and users that
-- already exist.
--
-- Load (re-running reloads from scratch; add -v scale=21 for ~100 000 rows):
--   docker compose exec -T db psql -U synapxia -d synapxia -v ON_ERROR_STOP=1 \
--     < specs/008-usage-metrics/synthetic-usage.sql
-- Remove:
--   docker compose exec -T db psql -U synapxia -d synapxia -v ON_ERROR_STOP=1 \
--     < specs/008-usage-metrics/synthetic-usage-remove.sql
--
-- Every row it writes carries `"synthetic": true` in its payload; that marker is
-- the only thing the remove script looks at, so real executions are never touched.
--
-- What the ~365 days of runs look like:
--   - spread over the active Published dashboards, with uneven popularity
--     (seeded: GenAI Adoption by Development Team > by Team > by Role);
--   - by the active users, uneven: ~10% power users who adopted early, occasional
--     users who start on a random day, and ~12% who never run anything;
--   - adoption grows over the year; weekends are quiet; dips around Christmas
--     and Holy Week; business hours (America/Bogota) with morning/afternoon peaks;
--   - outcomes in plausible shares with the messages the Catalog really writes:
--     Success, Failed (popup blocked / tab not opened / required value), Timeout
--     only on Internal Page dashboards, Cancelled, a few Incomplete (status NULL),
--     and Unauthorized on dashboards not shared with everyone; failures fall over
--     the year;
--   - payload in the Catalog's shape {values, sources, mode}, built from each
--     dashboard's own parameters.
-- Deterministic: setseed() makes every load identical for the same current_date
-- and the same dashboards/users.
-- =============================================================================
\set ON_ERROR_STOP on
-- Optional volume multiplier for the SC-003 benchmark (-v scale=21 ≈ 100 000 rows).
\if :{?scale}
\else
\set scale 1
\endif
BEGIN;

-- 0. Remove a previous load ------------------------------------------------------
DELETE FROM executions WHERE payload @> '{"synthetic": true}'::jsonb;

SELECT setseed(0.2026);

-- 1. Dashboards that receive runs: the active Published ones -----------------------
CREATE TEMP TABLE synth_dash ON COMMIT DROP AS
SELECT d.id AS dash_id,
       CASE WHEN d.sources_types = 'INTERNAL_PAGE' THEN 'VIEWER' ELSE 'TAB' END AS mode,
       -- popularity: the seeded GenAI dashboards get their own weights; others 1
       CASE d.id WHEN 1 THEN 3.0 WHEN 3 THEN 2.0 WHEN 2 THEN 1.5 ELSE 1.0 END AS base_w,
       -- not shared with everyone: some people reach it without a grant
       NOT EXISTS (SELECT 1 FROM dashboard_permissions p
                    WHERE p.dashboard = d.id AND p.target_type = 'PUBLIC'
                      AND (p.valid_to IS NULL OR p.valid_to > NOW())) AS restricted
  FROM dashboards d
 WHERE d.is_active AND d.status = 'PUBLISHED';

-- 2. Who runs dashboards: every active user, unevenly ------------------------------
CREATE TEMP TABLE synth_pool ON COMMIT DROP AS
SELECT q.user_id,
       CASE WHEN q.r1 < 0.12 THEN 0          -- never runs anything
            WHEN q.r1 < 0.22 THEN 8          -- power user
            WHEN q.r1 < 0.50 THEN 2.5
            ELSE 1 END AS w,
       CASE WHEN q.r1 >= 0.12 AND q.r1 < 0.22 THEN floor(q.r2 * 60)
            ELSE floor(q.r2 * 330) END AS adopt_day
  FROM (SELECT u.id AS user_id, random() AS r1, random() AS r2
          FROM users u WHERE u.is_active ORDER BY u.id) q;
-- The admin account is a light, steady user.
UPDATE synth_pool SET w = 1, adopt_day = 0
 WHERE user_id = (SELECT id FROM users WHERE username = 'admin');

-- 3. How many runs per day ----------------------------------------------------------
CREATE TEMP TABLE synth_runs ON COMMIT DROP AS
WITH days AS (
    SELECT i AS day_idx, (CURRENT_DATE - 364 + i) AS d FROM generate_series(0, 364) AS i
), counts AS (
    SELECT day_idx, d,
           round(30 * :scale
               * (0.22 + 0.78 * power(day_idx / 364.0, 0.9))              -- adoption grows
               * CASE extract(isodow FROM d)                              -- weekly rhythm
                     WHEN 6 THEN 0.07 WHEN 7 THEN 0.03 WHEN 1 THEN 1.1 WHEN 5 THEN 0.8
                     ELSE 1 END
               * CASE WHEN (extract(month FROM d) = 12 AND extract(day FROM d) >= 20)
                        OR (extract(month FROM d) = 1 AND extract(day FROM d) <= 9)
                      THEN 0.3                                            -- Christmas
                      WHEN d BETWEEN '2026-03-30' AND '2026-04-03'
                        OR d BETWEEN '2027-03-22' AND '2027-03-26'
                      THEN 0.35                                           -- Holy Week
                      ELSE 1 END
               * (0.75 + 0.5 * random()))::INT AS n
      FROM days
)
SELECT c.day_idx, c.d FROM counts c, generate_series(1, c.n) AS g(k) WHERE c.n > 0;

-- 4. Each run: who, which dashboard, when ---------------------------------------
CREATE TEMP TABLE synth_exec ON COMMIT DROP AS
SELECT r.day_idx, r.d, p.user_id, dpick.dash_id, dpick.mode, dpick.restricted,
       (r.d + make_interval(
            hours => (CASE WHEN h.r < 0.45 THEN 9 + floor(h.r2 * 3)
                           WHEN h.r < 0.80 THEN 14 + floor(h.r2 * 3)
                           ELSE 7 + floor(h.r2 * 12) END)::INT,
            mins  => floor(random() * 60)::INT,
            secs  => random() * 60)) AT TIME ZONE 'America/Bogota' AS executed_at,
       random() AS s, random() AS t, 1 - 0.5 * r.day_idx / 364.0 AS f
  FROM synth_runs r
  CROSS JOIN LATERAL (SELECT random() AS r, random() AS r2, r.day_idx AS dep) h
  CROSS JOIN LATERAL (
      SELECT sp.user_id FROM synth_pool sp
       WHERE sp.w > 0 AND sp.adopt_day <= r.day_idx
       ORDER BY -ln(1 - random()) / sp.w
       LIMIT 1) p
  CROSS JOIN LATERAL (
      SELECT sd.dash_id, sd.mode, sd.restricted FROM synth_dash sd
       WHERE r.day_idx >= 0
       ORDER BY -ln(1 - random()) / sd.base_w
       LIMIT 1) dpick;
DELETE FROM synth_exec WHERE executed_at > NOW();

-- 5. Outcome, failure kind, duration, message -------------------------------------
ALTER TABLE synth_exec ADD COLUMN outcome TEXT, ADD COLUMN failure TEXT,
                       ADD COLUMN duration_ms INT, ADD COLUMN error_message TEXT;
UPDATE synth_exec e SET outcome = CASE
        WHEN e.s < 0.012 THEN 'INCOMPLETE'
        WHEN e.restricted AND e.s < 0.10 THEN 'UNAUTHORIZED'
        WHEN e.s < 0.012 + 0.045 * e.f THEN 'FAILED'
        WHEN e.mode = 'VIEWER' AND e.s < 0.012 + 0.110 * e.f THEN 'TIMEOUT'
        WHEN e.s < 0.012 + 0.110 * e.f + 0.08 THEN 'CANCELLED'
        ELSE 'SUCCESS' END,
    failure = CASE WHEN e.mode = 'VIEWER' OR e.t >= 0.80 THEN 'REQUIRED'
                   WHEN e.t < 0.70 THEN 'POPUP' ELSE 'TAB' END;

UPDATE synth_exec e SET
    duration_ms = CASE e.outcome
        WHEN 'SUCCESS' THEN CASE WHEN e.mode = 'VIEWER'
                                 THEN least(29000, 1800 + round(3500 * -ln(1 - random())))
                                 ELSE least(6000, 350 + round(900 * -ln(1 - random()))) END
        WHEN 'TIMEOUT'   THEN 30000 + floor(random() * 400)
        WHEN 'CANCELLED' THEN least(300000, 1500 + round(15000 * -ln(1 - random())))
        WHEN 'FAILED'    THEN CASE WHEN e.failure = 'REQUIRED' THEN NULL
                                   ELSE 200 + floor(random() * 700) END
        ELSE NULL END,                                   -- UNAUTHORIZED / INCOMPLETE
    error_message = CASE
        WHEN e.outcome = 'UNAUTHORIZED' THEN format('Access to dashboard %s is not granted.', e.dash_id)
        WHEN e.outcome = 'TIMEOUT' THEN 'Did not load within 30 s'
        WHEN e.outcome = 'FAILED' AND e.failure = 'POPUP' THEN 'Popup blocked'
        WHEN e.outcome = 'FAILED' AND e.failure = 'TAB' THEN 'The new tab could not be opened'
        WHEN e.outcome = 'FAILED' THEN coalesce(
             (SELECT format('''%s'' is required', p.label) FROM parameters p
               WHERE p.dashboard = e.dash_id AND p.is_active AND p.is_required
               ORDER BY p.name LIMIT 1), 'Popup blocked')
        ELSE NULL END;

-- 6. Write the executions with a Catalog-shaped payload ---------------------------
INSERT INTO executions (dashboard, user_id, executed_at, payload, status, error_message, duration_ms)
SELECT e.dash_id, e.user_id, e.executed_at,
       CASE WHEN e.outcome = 'UNAUTHORIZED'
              OR (e.outcome = 'FAILED' AND e.error_message LIKE '%is required')
            -- refused at start: the Catalog stores only the submitted values
            THEN jsonb_build_object('values', v.vals, 'synthetic', TRUE)
            ELSE jsonb_build_object('values', v.vals, 'sources', v.srcs,
                                    'mode', e.mode, 'synthetic', TRUE) END,
       NULLIF(e.outcome, 'INCOMPLETE'), e.error_message, e.duration_ms
  FROM synth_exec e
  CROSS JOIN LATERAL (
      SELECT coalesce(jsonb_object_agg(pv.name, pv.val) FILTER (WHERE pv.val IS NOT NULL), '{}') AS vals,
             coalesce(jsonb_object_agg(pv.name, CASE WHEN pv.val = pv.default_value
                                                     THEN 'DEFAULT' ELSE 'INPUT' END)
                      FILTER (WHERE pv.val IS NOT NULL), '{}') AS srcs
        FROM (SELECT p.name, p.default_value, CASE
                  WHEN e.outcome = 'FAILED' AND p.is_required
                       AND e.error_message = format('''%s'' is required', p.label) THEN NULL
                  WHEN p.data_type = 'DATE' AND p.name LIKE '%from'
                       THEN to_char(e.d - (30 * (1 + floor(random() * 6)))::INT, 'YYYY-MM-DD')
                  WHEN p.data_type = 'DATE' THEN to_char(e.d, 'YYYY-MM-DD')
                  WHEN p.name = 'team' AND random() < 0.7
                       THEN (ARRAY['ALPHA','BRAVO','CHARLIE','DELTA','ECHO'])[1 + floor(random() * 5)::INT]
                  WHEN p.name = 'role' AND random() < 0.6
                       THEN (ARRAY['BACK','FRONT','QA','PLAT'])[1 + floor(random() * 4)::INT]
                  WHEN p.name = 'granularity' AND random() < 0.3
                       THEN (ARRAY['DAY','WEEK','MONTH'])[1 + floor(random() * 3)::INT]
                  ELSE NULLIF(p.default_value, '') END AS val
                FROM parameters p
               WHERE p.dashboard = e.dash_id AND p.is_active AND p.context_binding IS NULL
                 AND e.day_idx >= 0) pv
  ) v
 ORDER BY e.executed_at;

COMMIT;

-- Summary ---------------------------------------------------------------------------
SELECT coalesce(status, '(incomplete)') AS status, count(*) AS runs,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1) AS pct
  FROM executions WHERE payload @> '{"synthetic": true}'::jsonb
 GROUP BY 1 ORDER BY 2 DESC;
