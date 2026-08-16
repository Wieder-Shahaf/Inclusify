-- 007: Clean-text score per analysis run.
--
-- score = 100 * (1 - flagged_chars / total_chars), computed by the backend at
-- analysis time from the union of finding spans (overlaps merged). Stored so
-- history never recomputes it with a different formula. NULL for runs that
-- predate this migration and for failed runs.
--
-- Additive + idempotent: safe to run on a live database.

ALTER TABLE analysis_runs
  ADD COLUMN IF NOT EXISTS score NUMERIC(5,2)
  CHECK (score IS NULL OR (score >= 0 AND score <= 100));
