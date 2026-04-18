-- Migration 005: Remove 'paste' from input_type — only file formats are valid
--
-- Usage:
--   psql "$DATABASE_URL" -f db/migrations/005_remove_paste_input_type.sql

BEGIN;

ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_input_type_check;

ALTER TABLE documents
  ADD CONSTRAINT documents_input_type_check
  CHECK (input_type IN ('pdf', 'docx', 'pptx', 'txt'));

COMMIT;
