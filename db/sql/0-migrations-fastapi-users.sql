-- Migration: FastAPI-Users Configuration
-- This migration ensures FastAPI-Users compatibility
-- Note: is_superuser column is already in the users table DDL,
-- so we only need to update the admin user credentials here

-- Update admin user to be a superuser with bcrypt hashed password
-- Password: Admin123! 
-- Hash generated using: python hash_password.py
UPDATE users 
SET 
    is_superuser = TRUE,
    password_hash = '$2b$12$k8O7LZrGJgL/Vz0mKKT2t.VHGz8DpS2VKGZKjKT3Q8VL0GKmCp2Ua',
    updated_at = NOW()
WHERE username = 'admin' AND email = 'admin@synapxia.org';

-- Ensure this migration is idempotent - don't fail if column already exists
-- Column already exists in users table definition from 1-admin-ddl.sql
