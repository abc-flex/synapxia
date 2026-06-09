-- ============================================================================
-- Refresh tokens table (fastapi-users DatabaseStrategy storage)
-- ----------------------------------------------------------------------------
-- Backs the long-lived refresh-token flow: a successful /api/auth/login issues
-- both a short-lived JWT access token (60 min) and a long-lived refresh token
-- (14 days) stored here. The UI exchanges the refresh token for a new access
-- token via POST /api/auth/refresh/login when the access token expires.
--
-- Column shape matches fastapi-users' SQLAlchemyBaseAccessTokenTable so the
-- SQLAlchemyAccessTokenDatabase adapter can read/write directly.
-- ============================================================================

CREATE TABLE IF NOT EXISTS refresh_tokens (
    token       VARCHAR(43) PRIMARY KEY,                           -- secrets.token_urlsafe(32) → 43 chars
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id    ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_created_at ON refresh_tokens(created_at);
