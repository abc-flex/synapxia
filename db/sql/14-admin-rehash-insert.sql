-- Phase 2: Re-seed admin user with bcrypt hash (fixes SCRAM-SHA-256 seed bug)
-- The current admin password_hash is a PostgreSQL SCRAM-SHA-256 hash, which cannot be
-- verified by fastapi-users' bcrypt verifier. This migration replaces it with a proper
-- bcrypt hash of "Admin123!".
--
-- The bcrypt hash below was generated using:
--   import bcrypt
--   password = b"Admin123!"
--   hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))
--   print(hashed.decode())
--
-- Hash value: $2b$12$Q/ZWUi06lisvmpto32xbm.5r.ynn8fDfJ1fnLEPoBQqX.BqFAL5tG
--
-- Idempotent update: only changes if the current hash is still a SCRAM hash.
UPDATE users
SET password_hash = '$2b$12$Q/ZWUi06lisvmpto32xbm.5r.ynn8fDfJ1fnLEPoBQqX.BqFAL5tG'
WHERE username = 'admin' AND password_hash LIKE 'SCRAM-%';
