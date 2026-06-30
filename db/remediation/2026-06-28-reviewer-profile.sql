-- Remediation: add the new `REVIEWER` profile (+ its LIB/TAXO privileges) to an
-- ALREADY INITIALIZED database (e.g. the deployed Neon prod/dev DB).
--
-- WHY THIS EXISTS
--   The `REVIEWER` profile is seeded in db/sql/12-admin-insert.sql, but that
--   file only runs on a FRESH volume (`make rebuild` locally). The existing
--   Neon DB was initialized before this profile existed, so it never received
--   the row. Symptom: the Propose form's reviewer dropdown stays empty / has
--   no dedicated reviewer profile to assign the REVIEW/ASSIGNED action to.
--
--   (`propose_service.list_reviewers` already accepts ADMINISTRATOR /
--   ADMINISTRATIVE / REVIEWER / superuser, so admins populate the dropdown
--   today even without this; this seed adds the dedicated reviewer profile so
--   non-admin reviewer users can be created going forward.)
--
-- HOW TO APPLY (one-time, against the affected DB only)
--   Neon SQL console:  paste + Run.
--   psql:              psql "$NEON_DATABASE_URL" -f db/remediation/2026-06-28-reviewer-profile.sql
--
-- Idempotent: safe to run more than once. Fresh volumes already have these
-- rows (from 12-admin-insert.sql), so running this there is a no-op.

INSERT INTO profiles (code, name, description, icon)
VALUES
    ('REVIEWER',
     'Asset Reviewer',
     'Reviews proposed library assets before publication: can run the review workflow (review/modify/publish/reject) over digital assets, characterizations and actions.',
     'user-group')
ON CONFLICT (code) DO NOTHING;

INSERT INTO privileges (profile, module, option, can_edit)
VALUES
    -- TAXO (read-only — needs to see categories/features behind a proposal)
    ('REVIEWER','TAXO','CATEGORIES', FALSE),
    ('REVIEWER','TAXO','FEATURES',   FALSE),

    -- LIB (full edit — the review workflow lives here)
    ('REVIEWER','LIB','ASSETS',     TRUE),
    ('REVIEWER','LIB','PROMPTS',    TRUE),
    ('REVIEWER','LIB','MCPS',       TRUE),
    ('REVIEWER','LIB','AGENTS',     TRUE),
    ('REVIEWER','LIB','FLOWS',      TRUE),
    ('REVIEWER','LIB','SKILLS',     TRUE),
    ('REVIEWER','LIB','ASSISTANTS', TRUE),
    ('REVIEWER','LIB','RAG_APPS',   TRUE),
    ('REVIEWER','LIB','MODELS',     TRUE)
ON CONFLICT (profile, module, option) DO NOTHING;
