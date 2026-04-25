-- Migration 006: add file_storage_ref to store raw uploaded file blob reference
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS file_storage_ref TEXT;
