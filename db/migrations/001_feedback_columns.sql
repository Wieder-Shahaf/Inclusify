-- Migration: extend feedback table for per-flag thumbs up/down votes
-- Run: psql $DATABASE_URL -f db/migrations/001_feedback_columns.sql

BEGIN;

-- Allow feedback without a persisted run (private-mode analyses have no run_id)
ALTER TABLE feedback
  ALTER COLUMN run_id DROP NOT NULL;

-- Add per-flag context columns
ALTER TABLE feedback
  ADD COLUMN IF NOT EXISTS vote         TEXT CHECK (vote IN ('up','down')),
  ADD COLUMN IF NOT EXISTS flagged_text TEXT,
  ADD COLUMN IF NOT EXISTS severity     TEXT,
  ADD COLUMN IF NOT EXISTS start_idx    INT,
  ADD COLUMN IF NOT EXISTS end_idx      INT;

COMMIT;
