-- =============================================================================
-- SpecKit 008 (Usage Metrics): one-off changes for an ALREADY PROVISIONED database
-- (local volume created before this feature, or Neon). Fresh volumes get the same
-- indexes from db/sql/61-ana-ddl.sql. Safe to re-run.
--
--   docker compose exec -T db psql -U synapxia -d synapxia -v ON_ERROR_STOP=1 \
--     < specs/008-usage-metrics/provisioned-db.sql
--
-- Rollback:
--   DROP INDEX IF EXISTS ix_executions_executed_at, ix_executions_dashboard_executed_at;
-- =============================================================================
CREATE INDEX IF NOT EXISTS ix_executions_executed_at
    ON executions (executed_at);
CREATE INDEX IF NOT EXISTS ix_executions_dashboard_executed_at
    ON executions (dashboard, executed_at);
