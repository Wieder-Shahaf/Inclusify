import type { Annotation } from '@/components/AnnotatedText';
import type { Result } from '@/components/ResultCard';
import type { Severity } from '@/components/SeverityBadge';

const termMap: Array<{
  term: string;
  severity: Severity;
  explanation: string;
  suggestion?: string;
}> = [
  {
    term: 'homosexual',
    severity: 'outdated',
    explanation: 'The term is considered outdated and clinical in many contexts.',
    suggestion: 'Use "gay" or "lesbian" depending on context',
  },
  {
    term: 'transsexual',
    severity: 'outdated',
    explanation: 'The term is outdated and often perceived as medicalizing.',
    suggestion: 'Use "transgender person" or "trans person"',
  },
  {
    term: 'normal people',
    severity: 'biased',
    explanation: 'Implies LGBTQ+ people are abnormal by contrast.',
    suggestion: 'Use "non-LGBTQ+ people" or be specific',
  },
  {
    term: 'sexual preference',
    severity: 'factually_incorrect',
    explanation: 'Orientation is not a preference; "preference" is misleading.',
    suggestion: 'Use "sexual orientation"',
  },
  {
    term: 'born as a man',
    severity: 'potentially_offensive',
    explanation: 'Invalidates gender identity; phrasing can be disrespectful.',
    suggestion: 'Use "assigned male at birth (AMAB)"',
  },
];

export function mockAnalyze(text: string): {
  annotations: Annotation[];
  results: Result[];
  counts: Record<Severity, number>;
} {
  const annotations: Annotation[] = [];
  const results: Result[] = [];
  const seenPhrases = new Set<string>(); // Track unique phrases to avoid duplicate results
  const counts: Record<Severity, number> = {
    outdated: 0,
    biased: 0,
    potentially_offensive: 0,
    factually_incorrect: 0,
  };

  const lower = text.toLowerCase();
  for (const item of termMap) {
    let idx = 0;
    const needle = item.term.toLowerCase();
    const phraseKey = item.term.toLowerCase(); // Use lowercase for case-insensitive uniqueness
    
    while (idx !== -1) {
      idx = lower.indexOf(needle, idx);
      if (idx !== -1) {
        const end = idx + item.term.length;
        // Always add annotation for every occurrence
        annotations.push({
          start: idx,
          end,
          severity: item.severity,
          label: item.term,
          suggestion: item.suggestion,
          explanation: item.explanation,
          references: [
            { label: 'APA inclusive language', url: 'https://apastyle.apa.org/style-grammar-guidelines' },
          ],
        });
        
        // Only add result once per unique phrase
        if (!seenPhrases.has(phraseKey)) {
          seenPhrases.add(phraseKey);
          results.push({
            phrase: item.term,
            severity: item.severity,
            explanation: item.explanation,
            suggestion: item.suggestion,
            references: [
              { label: 'APA inclusive language', url: 'https://apastyle.apa.org/style-grammar-guidelines' },
            ],
          });
        }
        
        counts[item.severity] += 1;
        idx = end;
      }
    }
  }

  return { annotations, results, counts };
}
