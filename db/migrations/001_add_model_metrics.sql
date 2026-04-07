-- Migration 001: Add model_metrics table
-- Run once against the Azure PostgreSQL instance before deploying the
-- feature/model-performance-monitoring image.
--
-- Safe to re-run: IF NOT EXISTS guards prevent duplicate errors.
--
-- Usage:
--   psql "$DATABASE_URL" -f db/migrations/001_add_model_metrics.sql

BEGIN;

CREATE TABLE IF NOT EXISTS model_metrics (
  metric_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  analysis_mode         TEXT NOT NULL
    CHECK (analysis_mode IN ('llm', 'hybrid', 'rules_only')),

  total_sentences       INT  NOT NULL DEFAULT 0,
  llm_calls             INT  NOT NULL DEFAULT 0,
  llm_successes         INT  NOT NULL DEFAULT 0,
  llm_errors            INT  NOT NULL DEFAULT 0,
  llm_timeouts          INT  NOT NULL DEFAULT 0,
  circuit_breaker_trips INT  NOT NULL DEFAULT 0,

  avg_latency_ms        FLOAT,
  min_latency_ms        FLOAT,
  max_latency_ms        FLOAT,

  total_runtime_ms      INT,

  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_metrics_created_at
  ON model_metrics(created_at DESC);

COMMIT;
