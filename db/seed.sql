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

-- 4) Glossary terms (demo)
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
