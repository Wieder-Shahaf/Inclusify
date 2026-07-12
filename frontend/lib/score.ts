// Per-analysis clean-text score.
//
// score = 100 · (1 − flaggedChars / totalChars)
//
// The % of document characters NOT flagged by any finding. Flagged characters
// are the UNION of finding spans — overlapping or duplicate findings are
// merged so no character counts twice. All severities weigh equally by
// design: the score is a transparent, verifiable quantity ("99.2% of your
// text is inclusive"), and severity detail lives in the findings list.
//
// The backend computes and stores the canonical value per run
// (backend/app/modules/analysis/scoring.py — keep the two in sync);
// this mirror exists for demo mode and as a fallback.

export function computeCleanScore(
  spans: Array<{ start: number; end: number }>,
  totalChars: number,
): number {
  if (totalChars <= 0) return 100;

  const clamped = spans
    .map(({ start, end }) => ({ start: Math.max(0, start), end: Math.min(totalChars, end) }))
    .filter(({ start, end }) => end > start)
    .sort((a, b) => a.start - b.start);

  let flagged = 0;
  let curStart = -1;
  let curEnd = -1;
  for (const { start, end } of clamped) {
    if (start > curEnd) {
      if (curEnd >= 0) flagged += curEnd - curStart;
      curStart = start;
      curEnd = end;
    } else {
      curEnd = Math.max(curEnd, end);
    }
  }
  if (curEnd >= 0) flagged += curEnd - curStart;

  return Math.round(100 * (1 - flagged / totalChars) * 10) / 10;
}
