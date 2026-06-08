-- Phase 2: Add is_verified column for fastapi-users integration
ALTER TABLE users ADD COLUMN is_verified BOOLEAN NOT NULL DEFAULT FALSE;
