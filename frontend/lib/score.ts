// Per-analysis LGBTQ+ inclusivity score.
//
// The score is based on the *density* of weighted findings — weighted issues
// per 1,000 words — rather than the raw issue count. This keeps the score
// fair across document lengths: a 10,000-word paper and a 500-word abstract
// with the same rate of problematic language get the same score. An
// exponential curve maps density to 0–100 smoothly, so very dense documents
// still differentiate (no saturation at 0).
//
//   score = 100 · e^(−density / DENSITY_SCALE)
//
// Calibration (DENSITY_SCALE = 8):
//   density 0    → 100
//   density 0.85 →  90   (≈ one minor issue per 1,200 words — "Excellent")
//   density 2.9  →  70   ("Good" boundary)
//   density 5.5  →  50   ("Needs Improvement" boundary)
//   density 12   →  22
//
// TODO: tune DENSITY_SCALE and SEVERITY_WEIGHTS against the Achva
// expert-validated articles once the gold annotation set is extracted
// (see ACHVA-DATA-STRATEGY.md).

export type ScoreSeverity =
  | 'outdated'
  | 'biased'
  | 'potentially_offensive'
  | 'factually_incorrect';

// Aligned with the UI severity ordering (findings list sorts
// factually_incorrect as most severe).
export const SEVERITY_WEIGHTS: Record<ScoreSeverity, number> = {
  outdated: 1,
  biased: 2,
  potentially_offensive: 3,
  factually_incorrect: 4,
};

const DENSITY_SCALE = 8;

// Very short texts make density explode (one finding in 50 words → density 80);
// score them as if they were at least this long so a single finding in a
// pasted paragraph doesn't automatically read as 0.
const MIN_EFFECTIVE_WORDS = 300;

export function weightedIssueCount(counts: Record<ScoreSeverity, number>): number {
  return (Object.keys(SEVERITY_WEIGHTS) as ScoreSeverity[]).reduce(
    (sum, sev) => sum + (counts[sev] ?? 0) * SEVERITY_WEIGHTS[sev],
    0,
  );
}

export function computeInclusivityScore(
  counts: Record<ScoreSeverity, number>,
  wordCount: number,
): number {
  const weighted = weightedIssueCount(counts);
  if (weighted === 0) return 100;
  const effectiveWords = Math.max(wordCount, MIN_EFFECTIVE_WORDS);
  const densityPer1k = weighted / (effectiveWords / 1000);
  return Math.max(0, Math.min(100, Math.round(100 * Math.exp(-densityPer1k / DENSITY_SCALE))));
}
