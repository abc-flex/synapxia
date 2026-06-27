-- Remediation: add the missing `actions.workflow_status` column to an ALREADY
-- INITIALIZED database (e.g. the deployed Neon prod/dev DB).
--
-- WHY THIS EXISTS
--   `actions.workflow_status` is declared in db/sql/41-lib-ddl.sql, but that
--   column was added to the file *after* the Neon database had already been
--   initialized. The db/sql/*.sql migrations only run on a FRESH volume
--   (`make rebuild` locally), so the existing Neon DB never received the column.
--   Symptom: the header notification bell (list_notifications) and other
--   workflow-status reads fail with:
--       psycopg / asyncpg: column actions.workflow_status does not exist
--
-- HOW TO APPLY (one-time, against the affected DB only)
--   Neon SQL console:  paste + Run.
--   psql:              psql "$NEON_DATABASE_URL" -f db/remediation/2026-06-27-actions-workflow-status.sql
--
-- Idempotent: safe to run more than once. Fresh volumes already have the column
-- (from 41-lib-ddl.sql), so running this there is a no-op.

ALTER TABLE actions ADD COLUMN IF NOT EXISTS workflow_status VARCHAR(100);
-- references List_items.value where list = 'WORKFLOW_STATUS' (ASSIGNED/NOTIFIED/FINISHED/…)

-- If more "column/table does not exist" errors appear after this, the DB is
-- broadly behind the db/sql/ schema. Diff db/sql/ against the live schema and
-- apply the additive ALTER/CREATE IF NOT EXISTS set (needs DB access).
