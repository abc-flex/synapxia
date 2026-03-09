-- Migration: Add FastAPI-Users support
-- This migration adds the is_superuser column and updates admin user credentials

-- Add is_superuser column if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN NOT NULL DEFAULT FALSE;

-- Update admin user to be a superuser with bcrypt hashed password
-- Password: Admin123! (bcrypt hash)
-- Generate a new hash using: python hash_password.py
UPDATE users 
SET 
    is_superuser = TRUE,
    password_hash = '$2b$12$k8O7LZrGJgL/Vz0mKKT2t.VHGz8DpS2VKGZKjKT3Q8VL0GKmCp2Ua',
    updated_at = NOW()
WHERE username = 'admin' AND email = 'admin@synapxia.org';
