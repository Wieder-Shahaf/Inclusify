-- Migration 001: Add user profile fields
-- Apply to existing databases that were created from schema.sql before this change.

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS full_name TEXT,
  ADD COLUMN IF NOT EXISTS profession TEXT,
  ADD COLUMN IF NOT EXISTS institution TEXT;
