BEGIN;

-- UUID בלי uuid-ossp (יותר יציב לרוב)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) Organizations
CREATE TABLE organizations (
  org_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE,
  default_private_mode BOOLEAN NOT NULL DEFAULT TRUE,
  settings_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 2) Users
CREATE TABLE users (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,

  email TEXT UNIQUE NOT NULL,
  password_hash TEXT,
  sso_provider TEXT,

  role TEXT NOT NULL DEFAULT 'user'
    CHECK (role IN ('user','org_admin','site_admin')),

  locale TEXT DEFAULT 'he',
  consent_store_text BOOLEAN NOT NULL DEFAULT FALSE,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  last_login_at TIMESTAMP
);

CREATE INDEX idx_users_org ON users(org_id);

-- 3) Documents
CREATE TABLE documents (
  document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,

  input_type TEXT NOT NULL CHECK (input_type IN ('paste','upload')),
  language TEXT NOT NULL DEFAULT 'auto' CHECK (language IN ('he','en','auto')),

  private_mode BOOLEAN NOT NULL DEFAULT TRUE,

  original_filename TEXT,
  mime_type TEXT,

  text_storage_ref TEXT,
  text_sha256 TEXT,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMP,
  expires_at TIMESTAMP
);

CREATE INDEX idx_documents_org_created ON documents(org_id, created_at);
CREATE INDEX idx_documents_user_created ON documents(user_id, created_at);

-- 4) Configurations
CREATE TABLE configs (
  config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,

  name TEXT NOT NULL,
  config_json JSONB NOT NULL DEFAULT '{}'::jsonb,

  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_configs_org ON configs(org_id);

-- 5) Analysis Runs
CREATE TABLE analysis_runs (
  run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
  config_id UUID REFERENCES configs(config_id) ON DELETE SET NULL,

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

  run_id UUID NOT NULL REFERENCES analysis_runs(run_id) ON DELETE CASCADE,
  finding_id UUID REFERENCES findings(finding_id) ON DELETE SET NULL,
  user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,

  feedback_type TEXT NOT NULL
    CHECK (feedback_type IN ('helpful','false_positive','false_negative')),

  comment TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feedback_run ON feedback(run_id);
CREATE INDEX idx_feedback_finding ON feedback(finding_id);
CREATE INDEX idx_feedback_type ON feedback(feedback_type);

-- 13) Usage Events
CREATE TABLE usage_events (
  event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,

  event_type TEXT NOT NULL,
  event_at TIMESTAMP NOT NULL DEFAULT NOW(),

  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_events_org_time ON usage_events(org_id, event_at);
CREATE INDEX idx_events_type_time ON usage_events(event_type, event_at);

-- 14) Audit Log
CREATE TABLE audit_log (
  audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  org_id UUID REFERENCES organizations(org_id) ON DELETE SET NULL,
  actor_user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,

  action TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id UUID,

  at TIMESTAMP NOT NULL DEFAULT NOW(),
  ip_hash TEXT,
  details_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_audit_org_time ON audit_log(org_id, at);
CREATE INDEX idx_audit_actor_time ON audit_log(actor_user_id, at);

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

CREATE TRIGGER trg_orgs_updated
BEFORE UPDATE ON organizations
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_rules_updated
BEFORE UPDATE ON rules
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_glossary_updated
BEFORE UPDATE ON glossary_terms
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
