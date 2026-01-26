-- =====================================
-- Seed data for Inclusify
-- =====================================

-- 1) Source (guidelines)
INSERT INTO guideline_sources (name, publisher, url, last_reviewed_at)
VALUES (
  'Inclusive language guideline (demo)',
  'Inclusify',
  'https://example.com/guideline',
  NOW()
);

-- 2) Organization
INSERT INTO organizations (name, slug, default_private_mode, settings_json)
VALUES (
  'Demo Organization',
  'demo-org',
  TRUE,
  '{"default_language":"he","store_text_default":false}'::jsonb
);

-- 3) Admin user (demo)
INSERT INTO users (org_id, email, role, locale, consent_store_text)
SELECT org_id, 'admin@demo.org', 'org_admin', 'he', FALSE
FROM organizations
WHERE slug='demo-org';

-- 4) Demo rules (a few examples)
INSERT INTO rules (
  language, name, description, category, default_severity,
  pattern_type, pattern_value, example_bad, example_good,
  is_enabled, source_id
)
SELECT
  'he',
  'כינויי גוף ניטרליים',
  'העדפה לניסוח כולל/ניטרלי כשאפשר.',
  'pronouns',
  'medium',
  'keyword',
  'הוא/היא',
  'הוא/היא יכול/ה להגיש את הטופס',
  'אפשר להגיש את הטופס',
  TRUE,
  s.source_id
FROM guideline_sources s
WHERE s.name='Inclusive language guideline (demo)';

INSERT INTO rules (
  language, name, description, category, default_severity,
  pattern_type, pattern_value, example_bad, example_good,
  is_enabled, source_id
)
SELECT
  'he',
  'מונח פוגעני (דמו)',
  'דוגמה בלבד לחוק שמסמן מונח בעייתי.',
  'derogatory',
  'high',
  'keyword',
  '***',
  'השתמשת במונח ***',
  'השתמשת במונח חלופי מכבד',
  TRUE,
  s.source_id
FROM guideline_sources s
WHERE s.name='Inclusive language guideline (demo)';

-- 5) Glossary terms (demo)
INSERT INTO glossary_terms (language, term, definition, inclusive_alternative, tags, source_id)
SELECT
  'he',
  'להט"ב',
  'ראשי תיבות לקהילה הגאה.',
  'קהילה גאה',
  '["community","hebrew"]'::jsonb,
  s.source_id
FROM guideline_sources s
WHERE s.name='Inclusive language guideline (demo)';
