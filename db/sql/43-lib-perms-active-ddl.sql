-- **********************************
-- ** Library: asset_permissions ****
-- **********************************
--
-- Additive: give asset_permissions a logical-delete flag so the API can
-- soft-delete grants (is_active=False) like every other lib table, instead
-- of a hard DELETE. The valid_from/valid_to columns keep their separate
-- temporal-validity meaning. Idempotent so it is safe to re-run.

ALTER TABLE asset_permissions
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
