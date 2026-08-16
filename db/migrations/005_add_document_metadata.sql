-- Migration 003: Add title, author, page_count columns to documents
-- These metadata fields are extracted during ingestion (Docling / PDF headers).
--
-- Safe to re-run: IF NOT EXISTS guards prevent duplicate errors.
--
-- Usage:
--   psql "$DATABASE_URL" -f db/migrations/003_add_document_metadata.sql

BEGIN;

ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS title TEXT,
  ADD COLUMN IF NOT EXISTS author TEXT,
  ADD COLUMN IF NOT EXISTS page_count INT CHECK (page_count IS NULL OR page_count >= 0);

COMMIT;
