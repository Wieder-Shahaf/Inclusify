import type { Annotation } from '@/components/AnnotatedText';
import type { Severity } from '@/components/SeverityBadge';
import type { AnalysisResult } from '@/lib/api/client';

/**
 * Dev-only sample analysis used to preview the results view (especially the
 * mobile report) without a running backend. Gated behind `?demo=1` AND
 * NODE_ENV !== 'production' in the analyze page — never shipped to users.
 */

export const DEMO_FILE_NAME = 'sample_academic_paper.txt';

const DEMO_TEXT = `Recent studies on homosexuals have explored how sexual preference develops over time. Several researchers framed it as a lifestyle choice rather than an identity. Earlier literature described transsexuals as suffering from gender identity disorder, a clinical condition. When compared against the normal population, these groups were often pathologized.`;

type DemoFinding = {
  phrase: string;
  severity: Severity;
  category?: string;
  explanation: string;
  suggestion?: string;
  references?: Array<{ label: string; url: string }>;
};

const FINDINGS: DemoFinding[] = [
  {
    phrase: 'homosexuals',
    severity: 'outdated',
    explanation: 'Using "homosexuals" as a noun is clinical and dated; it reduces people to a category.',
    suggestion: 'gay people / lesbian and gay people',
  },
  {
    phrase: 'sexual preference',
    severity: 'biased',
    category: 'Generalization',
    explanation: '"Preference" implies sexual orientation is a choice rather than an inherent trait.',
    suggestion: 'sexual orientation',
  },
  {
    phrase: 'lifestyle choice',
    severity: 'potentially_offensive',
    category: 'Demeaning Terminology',
    explanation: 'Framing identity as a "lifestyle choice" is a well-documented dismissive trope.',
    suggestion: 'identity',
  },
  {
    phrase: 'transsexuals',
    severity: 'outdated',
    explanation: 'Often considered outdated; many prefer "transgender people".',
    suggestion: 'transgender people',
  },
  {
    phrase: 'gender identity disorder',
    severity: 'factually_incorrect',
    category: 'Medicalization',
    explanation: 'This diagnosis was replaced by "gender dysphoria"; being transgender is not a disorder.',
    suggestion: 'gender dysphoria',
    references: [{ label: 'DSM-5', url: 'https://www.psychiatry.org/psychiatrists/practice/dsm' }],
  },
  {
    phrase: 'normal population',
    severity: 'biased',
    category: 'Generalization',
    explanation: 'Implies LGBTQ+ people are abnormal by contrast.',
    suggestion: 'cisgender and heterosexual population',
  },
];

export function buildDemoAnalysis(): { text: string; result: AnalysisResult } {
  const annotations: Annotation[] = FINDINGS.map((f, i) => {
    const start = DEMO_TEXT.indexOf(f.phrase);
    return {
      start: start >= 0 ? start : i,
      end: (start >= 0 ? start : i) + f.phrase.length,
      severity: f.severity,
      label: f.phrase,
      category: f.category,
      suggestion: f.suggestion,
      explanation: f.explanation,
      confidence: 0.6,
      references: f.references,
    };
  });

  const counts: Record<Severity, number> = {
    outdated: 0, biased: 0, potentially_offensive: 0, factually_incorrect: 0,
  };
  for (const f of FINDINGS) counts[f.severity]++;

  return {
    text: DEMO_TEXT,
    result: {
      annotations,
      results: FINDINGS,
      counts,
      originalText: DEMO_TEXT,
      analysisMode: 'llm',
      runId: 'demo-run',
    },
  };
}
