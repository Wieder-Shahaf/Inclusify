BEGIN;

-- UUID בלי uuid-ossp (יותר יציב לרוב)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) Users
CREATE TABLE users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  email TEXT UNIQUE NOT NULL,
  password_hash TEXT,
  sso_provider TEXT,

  role TEXT NOT NULL DEFAULT 'user'
    CHECK (role IN ('user','site_admin')),

  -- FastAPI Users required fields
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
  is_verified BOOLEAN NOT NULL DEFAULT FALSE,

  full_name TEXT,
  profession TEXT,
  institution TEXT,

  locale TEXT DEFAULT 'he',
  consent_store_text BOOLEAN NOT NULL DEFAULT FALSE,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  last_login_at TIMESTAMP
);

-- 2b) OAuth Accounts (FastAPI Users)
CREATE TABLE oauth_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  oauth_name TEXT NOT NULL,
  access_token TEXT NOT NULL DEFAULT '',
  expires_at INT,
  refresh_token TEXT,
  account_id TEXT NOT NULL,
  account_email TEXT NOT NULL
);

CREATE INDEX idx_oauth_user ON oauth_accounts(user_id);

-- 3) Documents
CREATE TABLE documents (
  document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,

  input_type TEXT NOT NULL CHECK (input_type IN ('paste','upload')),
  language TEXT NOT NULL DEFAULT 'auto' CHECK (language IN ('he','en','auto')),

  private_mode BOOLEAN NOT NULL DEFAULT TRUE,

  original_filename TEXT,
  mime_type TEXT,
  title TEXT,
  author TEXT,
  page_count INT CHECK (page_count IS NULL OR page_count >= 0),
  detected_language TEXT CHECK (detected_language IS NULL OR detected_language IN ('he','en')),

  text_storage_ref TEXT,
  text_sha256 TEXT,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMP,
  expires_at TIMESTAMP
);

CREATE INDEX idx_documents_user_created ON documents(user_id, created_at);

-- 4) Analysis Runs
CREATE TABLE analysis_runs (
  run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,

  status TEXT NOT NULL CHECK (status IN ('queued','running','succeeded','failed')),

  model_version TEXT NOT NULL,
  runtime_ms INT CHECK (runtime_ms IS NULL OR runtime_ms >= 0),

  config_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,

  started_at TIMESTAMP,
  finished_at TIMESTAMP,

  error_code TEXT,
  error_message TEXT
);

CREATE INDEX idx_runs_document ON analysis_runs(document_id);
CREATE INDEX idx_runs_status ON analysis_runs(status);

-- 6) Guideline Sources
CREATE TABLE guideline_sources (
  source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  publisher TEXT,
  url TEXT,
  last_reviewed_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 7) Rules
CREATE TABLE rules (
  rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  language TEXT NOT NULL CHECK (language IN ('he','en')),
  name TEXT NOT NULL,
  description TEXT,

  category TEXT NOT NULL,
  default_severity TEXT NOT NULL DEFAULT 'medium'
    CHECK (default_severity IN ('low','medium','high')),

  pattern_type TEXT NOT NULL CHECK (pattern_type IN ('regex','keyword','prompt','other')),
  pattern_value TEXT NOT NULL,

  example_bad TEXT,
  example_good TEXT,

  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,

  source_id UUID REFERENCES guideline_sources(source_id) ON DELETE SET NULL,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rules_language ON rules(language);
CREATE INDEX idx_rules_enabled ON rules(is_enabled);

-- 8) Findings
CREATE TABLE findings (
  finding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,

  category TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('low','medium','high')),

  start_idx INT NOT NULL CHECK (start_idx >= 0),
  end_idx INT NOT NULL CHECK (end_idx > start_idx),

  confidence DOUBLE PRECISION CHECK (confidence IS NULL OR (confidence BETWEEN 0 AND 1)),

  explanation TEXT,
  rule_id UUID REFERENCES rules(rule_id) ON DELETE SET NULL,

  excerpt_redacted TEXT,

  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_findings_run ON findings(run_id);

-- 9) Suggestions
CREATE TABLE suggestions (
  suggestion_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  finding_id UUID NOT NULL REFERENCES findings(finding_id) ON DELETE CASCADE,

  language TEXT NOT NULL CHECK (language IN ('he','en')),
  replacement_text TEXT NOT NULL,
  rationale TEXT,

  source_id UUID REFERENCES guideline_sources(source_id) ON DELETE SET NULL,

  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_suggestions_finding ON suggestions(finding_id);

-- 10) Glossary
CREATE TABLE glossary_terms (
  term_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  language TEXT NOT NULL CHECK (language IN ('he','en')),
  term TEXT NOT NULL,
  definition TEXT,
  inclusive_alternative TEXT,

  tags JSONB NOT NULL DEFAULT '[]'::jsonb,

  source_id UUID REFERENCES guideline_sources(source_id) ON DELETE SET NULL,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

  UNIQUE(language, term)
);

CREATE INDEX idx_glossary_language ON glossary_terms(language);

-- 11) Report Exports
CREATE TABLE report_exports (
  export_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,

  format TEXT NOT NULL CHECK (format IN ('pdf','docx','json')),
  storage_ref TEXT NOT NULL,

  anonymized BOOLEAN NOT NULL DEFAULT TRUE,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP
);

CREATE INDEX idx_exports_run ON report_exports(run_id);

-- 12) Feedback
CREATE TABLE feedback (
  feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- run_id and finding_id are nullable: feedback can be submitted for in-memory
  -- analyses (private mode / DB not connected) where no run was persisted.
  run_id UUID REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
  finding_id UUID REFERENCES findings(finding_id) ON DELETE SET NULL,
  user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,

  feedback_type TEXT NOT NULL
    CHECK (feedback_type IN ('helpful','false_positive','false_negative')),

  -- Raw vote captured from the UI (up/down). feedback_type is the semantic label.
  vote TEXT CHECK (vote IN ('up','down')),

  flagged_text TEXT,
  severity TEXT,
  start_idx INT,
  end_idx INT,

  comment TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feedback_run ON feedback(run_id);
CREATE INDEX idx_feedback_finding ON feedback(finding_id);
CREATE INDEX idx_feedback_type ON feedback(feedback_type);

-- 13) Usage Events
CREATE TABLE usage_events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,

  event_type TEXT NOT NULL,
  event_at TIMESTAMP NOT NULL DEFAULT NOW(),

  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_events_type_time ON usage_events(event_type, event_at);

-- 14) Audit Log
CREATE TABLE audit_log (
  audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  actor_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,

  action TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id UUID,

  at TIMESTAMP NOT NULL DEFAULT NOW(),
  ip_hash TEXT,
  details_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_audit_actor_time ON audit_log(actor_user_id, at);

-- 15) Model Performance Metrics
-- Stores per-request vLLM inference metrics for admin monitoring.
-- Persisted for ALL analyses (including private_mode=True) — privacy mode
-- protects text content, not aggregate timing data. run_id is omitted
-- intentionally to keep this table fully decoupled from the documents/runs flow.
CREATE TABLE model_metrics (
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

CREATE INDEX idx_model_metrics_created_at ON model_metrics(created_at DESC);

-- Privacy constraint
ALTER TABLE documents
ADD CONSTRAINT chk_private_storage
CHECK (
  (private_mode = TRUE AND text_storage_ref IS NULL)
  OR
  (private_mode = FALSE)
);

-- updated_at trigger
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_rules_updated
BEFORE UPDATE ON rules
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_glossary_updated
BEFORE UPDATE ON glossary_terms
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
