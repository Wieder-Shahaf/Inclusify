-- Migration 004: Expand input_type values to include file format types
-- Replaces the binary paste/upload constraint with granular format values.
--
-- Safe to re-run: constraint drop is idempotent via IF EXISTS.
--
-- Usage:
--   psql "$DATABASE_URL" -f db/migrations/004_update_input_type_constraint.sql

BEGIN;

ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_input_type_check;

ALTER TABLE documents
  ADD CONSTRAINT documents_input_type_check
  CHECK (input_type IN ('paste', 'pdf', 'docx', 'pptx', 'txt'));

-- Backfill existing 'upload' rows to 'pdf' (safe assumption for legacy data)
UPDATE documents SET input_type = 'pdf' WHERE input_type = 'upload';

COMMIT;
