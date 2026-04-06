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

-- 2) Admin user (demo)
INSERT INTO users (email, role, locale, consent_store_text)
VALUES ('admin@demo.org', 'site_admin', 'he', FALSE);

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
