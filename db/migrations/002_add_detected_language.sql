-- Migration 002: Add detected_language column to documents
-- Complements the ingestion pipeline's language-detection feature so
-- the auto-detected language is persisted alongside the user-selected one.
--
-- Safe to re-run: IF NOT EXISTS guards prevent duplicate errors.
--
-- Usage:
--   psql "$DATABASE_URL" -f db/migrations/002_add_detected_language.sql

BEGIN;

ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS detected_language TEXT
  CHECK (detected_language IS NULL OR detected_language IN ('he','en'));

COMMIT;
