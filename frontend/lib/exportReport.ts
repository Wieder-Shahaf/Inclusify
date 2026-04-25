import type { Annotation } from '@/components/AnnotatedText';
import type { Severity } from '@/components/SeverityBadge';

// ── Palette ───────────────────────────────────────────────────────────────────
const PURPLE:       [number, number, number] = [88,  28,  135];
const PURPLE_LIGHT: [number, number, number] = [124, 58,  237];
const SLATE:        [number, number, number] = [71,  85,  105];
const SLATE_LIGHT:  [number, number, number] = [148, 163, 184];
const PAGE_BG:      [number, number, number] = [248, 246, 255];
const CARD_BG:      [number, number, number] = [255, 255, 255];
const CARD_SHADOW:  [number, number, number] = [233, 228, 250];

const SEVERITY_COLOR: Record<Severity, {
  border:  [number, number, number];
  pill_bg: [number, number, number];
  pill_fg: [number, number, number];
  bar:     [number, number, number];
  label:   [number, number, number];
}> = {
  outdated: {
    border:  [14,  165, 233],
    pill_bg: [224, 242, 254],
    pill_fg: [7,   89,  133],
    bar:     [56,  189, 248],
    label:   [2,   132, 199],
  },
  biased: {
    border:  [245, 158,  11],
    pill_bg: [255, 251, 235],
    pill_fg: [120, 53,   15],
    bar:     [251, 191,  36],
    label:   [180, 83,    9],
  },
  potentially_offensive: {
    border:  [249, 115,  22],
    pill_bg: [255, 237, 213],
    pill_fg: [124, 45,   18],
    bar:     [251, 146,  60],
    label:   [194, 65,    9],
  },
  factually_incorrect: {
    border:  [239, 68,   68],
    pill_bg: [254, 226, 226],
    pill_fg: [153, 27,   27],
    bar:     [248, 113, 113],
    label:   [185, 28,   28],
  },
};

const LLM_CAT_COLOR: Record<string, { pill_bg: [number,number,number]; pill_fg: [number,number,number] }> = {
  'Medicalization':        { pill_bg: [243, 232, 255], pill_fg: [107, 33, 168]  },
  'Generalization':        { pill_bg: [224, 231, 255], pill_fg: [67,  56, 202]  },
  'Demeaning Terminology': { pill_bg: [255, 228, 230], pill_fg: [159, 18,  57]  },
};

// ── Interfaces ────────────────────────────────────────────────────────────────
type ReportResult = {
  phrase:       string;
  severity:     Severity;
  category?:    string;
  explanation:  string;
  suggestion?:  string;
  references?:  Array<{ label: string; url: string }>;
};

interface AnalysisData {
  text: string;
  annotations: Annotation[];
  results?: ReportResult[];
  counts: Record<Severity, number>;
  summary: {
    totalIssues:     number;
    score:           number;
    recommendations: string[];
  };
}

interface ExportOptions {
  fileName:          string;
  locale?:           string;
  returnBase64?:     boolean;
  filteredResults?:  ReportResult[];
  visibleAnnotations?: Annotation[];
  displayScore?:     number;
  displayCounts?:    Record<Severity, number>;
  recommendations?:  string[];
  totalAvailableFindings?: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const REPORT_LABELS = {
  en: {
    title: 'FINDINGS',
    continued: 'FINDINGS (continued)',
    document: 'Document',
    score: 'LGBTQ+ INCLUSIVITY SCORE.',
    totalFindings: 'TOTAL FINDINGS',
    wordCount: 'WORD COUNT',
    findingsByCategory: 'Findings by Category',
    issueType: 'Issue type:',
    biasPattern: 'Bias pattern:',
    findings: 'Findings',
    excellent: 'Excellent',
    good: 'Good',
    needsWork: 'Needs Work',
    noFindings: 'No findings match the current report scope.',
    findingsRequireReview: 'findings require review before sharing.',
    suggestedFix: 'Suggested fix:',
    watermark: 'Achva LGBTQ+ Student Organization',
    severity: {
      outdated: 'Outdated',
      biased: 'Biased',
      potentially_offensive: 'Potentially Offensive',
      factually_incorrect: 'Factually Incorrect',
    },
    category: {
      Medicalization: 'Medicalization',
      Generalization: 'Generalization',
      'Demeaning Terminology': 'Demeaning Terminology',
    },
  },
  he: {
    title: 'ממצאים',
    continued: 'ממצאים (המשך)',
    document: 'מסמך',
    score: 'ציון הכללה לקהילת הלהט"ב.',
    totalFindings: 'סך ממצאים',
    wordCount: 'מספר מילים',
    findingsByCategory: 'ממצאים לפי קטגוריה',
    issueType: 'סוג ממצא:',
    biasPattern: 'דפוס הטיה:',
    findings: 'ממצאים',
    excellent: 'מצוין',
    good: 'טוב',
    needsWork: 'דורש שיפור',
    noFindings: 'אין ממצאים התואמים להיקף הדוח הנוכחי.',
    findingsRequireReview: 'ממצאים דורשים בדיקה לפני שיתוף.',
    suggestedFix: 'הצעה לתיקון:',
    watermark: 'ארגון אחווה להט״ב הסטודנטיאלי',
    severity: {
      outdated: 'מיושן',
      biased: 'מוטה',
      potentially_offensive: 'עלול לפגוע',
      factually_incorrect: 'שגוי עובדתית',
    },
    category: {
      Medicalization: 'מדיקליזציה',
      Generalization: 'הכללה',
      'Demeaning Terminology': 'מינוח פוגעני',
    },
  },
} as const;

function labelsFor(locale?: string) {
  return locale === 'he' ? REPORT_LABELS.he : REPORT_LABELS.en;
}

function clampScore(score: number): number {
  return Math.max(0, Math.min(100, Math.round(Number.isFinite(score) ? score : 0)));
}

function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

function countResults(results: ReportResult[]): Record<Severity, number> {
  const counts: Record<Severity, number> = {
    outdated: 0,
    biased: 0,
    potentially_offensive: 0,
    factually_incorrect: 0,
  };
  for (const result of results) {
    counts[result.severity] = (counts[result.severity] ?? 0) + 1;
  }
  return counts;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function textWidth(doc: any, text: string): number {
  return typeof doc.getTextWidth === 'function' ? doc.getTextWidth(text) : text.length * 2;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function splitLines(doc: any, text: string, width: number): string[] {
  if (!text) return [];
  if (typeof doc.splitTextToSize === 'function') {
    return doc.splitTextToSize(text, width) as string[];
  }
  const approxChars = Math.max(12, Math.floor(width / 1.8));
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let current = '';
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > approxChars && current) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current) lines.push(current);
  return lines;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function ellipsizeToWidth(doc: any, text: string, maxWidth: number): string {
  if (textWidth(doc, text) <= maxWidth) return text;
  const suffix = '...';
  let trimmed = text;
  while (trimmed.length > 0 && textWidth(doc, `${trimmed}${suffix}`) > maxWidth) {
    trimmed = trimmed.slice(0, -1);
  }
  return `${trimmed.trimEnd()}${suffix}`;
}

// Draw a filled pill (rounded-rect approximation: rect + circles at ends)
function fillPill(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  doc: any,
  x: number, y: number, w: number, h: number,
  color: [number, number, number],
) {
  const r = h / 2;
  doc.setFillColor(...color);
  doc.rect(x + r, y, w - 2 * r, h, 'F');
  doc.circle(x + r,     y + r, r, 'F');
  doc.circle(x + w - r, y + r, r, 'F');
}

// Draw text inside a filled pill badge; returns the total pill width used
function pillBadge(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  doc: any,
  x: number, y: number,
  text: string,
  bg: [number, number, number],
  fg: [number, number, number],
  fontSize: number,
): number {
  doc.setFontSize(fontSize);
  doc.setFont('helvetica', 'normal');
  const tw  = textWidth(doc, text);
  const ph  = fontSize * 0.55;     // pill height relative to font
  const px  = 2.2;                 // horizontal inner padding
  const pw  = tw + px * 2;
  const py  = y - ph * 0.82;
  fillPill(doc, x, py, pw, ph, bg);
  doc.setTextColor(...fg);
  doc.text(text, x + px, y);
  return pw + 1.5;                 // width + gap
}

// Gradient page background — very subtle lavender-to-white top-to-bottom
function drawPageBg(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  doc: any,
  pageWidth: number,
  pageHeight: number,
) {
  const steps = 40;
  const [r0, g0, b0] = PAGE_BG;
  for (let i = 0; i < steps; i++) {
    const t  = i / steps;
    const r  = Math.round(r0 + t * (255 - r0));
    const g  = Math.round(g0 + t * (255 - g0));
    const b  = Math.round(b0 + t * (255 - b0));
    doc.setFillColor(r, g, b);
    doc.rect(0, (i / steps) * pageHeight, pageWidth, pageHeight / steps + 0.5, 'F');
  }
}

// Card with shadow — white rounded-ish card on lavender background
function drawCard(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  doc: any,
  x: number, y: number, w: number, h: number,
) {
  doc.setFillColor(...CARD_SHADOW);
  doc.rect(x + 0.7, y + 0.7, w, h, 'F');
  doc.setFillColor(...CARD_BG);
  doc.rect(x, y, w, h, 'F');
}

// ── Main export function ──────────────────────────────────────────────────────
export async function exportReport(
  analysis:  AnalysisData,
  options:   ExportOptions,
): Promise<string | void> {
  const { jsPDF } = await import('jspdf');
  const { default: autoTable } = await import('jspdf-autotable');
  void autoTable; // imported for side-effects registration; individual calls use doc directly

  const doc        = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageWidth  = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const M          = 14;   // margin
  const CW         = pageWidth - M * 2; // content width

  const labels = labelsFor(options.locale);
  const displayResults = options.filteredResults ?? analysis.results ?? [];
  const displayCounts = options.displayCounts ?? countResults(displayResults);
  const displayScore = clampScore(options.displayScore ?? analysis.summary.score);
  const totalFindings = displayResults.length;

  // ── Page 1 background ────────────────────────────────────────────────────────
  drawPageBg(doc, pageWidth, pageHeight);

  let Y = M; // running Y cursor

  // ── Thin purple top accent bar ────────────────────────────────────────────────
  doc.setFillColor(...PURPLE);
  doc.rect(0, 0, pageWidth, 1.5, 'F');
  Y = 8;

  // ── Title row ─────────────────────────────────────────────────────────────────
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(17);
  doc.setTextColor(...PURPLE);
  doc.text(labels.title, M, Y + 6);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(...SLATE_LIGHT);
  const dateStr = `${options.fileName || labels.document} - ${new Date().toLocaleDateString('en-GB')}`;
  doc.text(dateStr, pageWidth - M, Y + 6, { align: 'right' });

  Y += 12;

  // ── Score card ────────────────────────────────────────────────────────────────
  const scoreCardH = 40;
  drawCard(doc, M, Y, CW, scoreCardH);

  const scoreColor: [number, number, number] =
    displayScore >= 80 ? [22, 163, 74] : displayScore >= 60 ? [202, 138, 4] : [220, 38, 38];
  const scoreLabel =
    displayScore >= 80 ? labels.excellent : displayScore >= 60 ? labels.good : labels.needsWork;

  const innerL = M + 6;
  const innerT = Y + 5;

  // Small caps label
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(6.5);
  doc.setTextColor(...SLATE_LIGHT);
  doc.text(labels.score, innerL, innerT + 4);

  // Large score number
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(33);
  doc.setTextColor(...scoreColor);
  doc.text(String(displayScore), innerL, innerT + 17);

  // /100
  const bigNumW = textWidth(doc, String(displayScore));
  doc.setFontSize(13);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...SLATE);
  doc.text('/100', innerL + bigNumW + 1.5, innerT + 17);

  // Status and short interpretation
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.setTextColor(...scoreColor);
  doc.text(scoreLabel, innerL, innerT + 25);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.setTextColor(...SLATE);
  const summaryText = `${totalFindings} ${labels.findingsRequireReview}`;
  doc.text(summaryText, innerL, innerT + 31);

  // Compact stat blocks on the right: no duplicate score visualization
  const statItems = [
    { label: labels.totalFindings, value: String(totalFindings) },
    { label: labels.wordCount, value: countWords(analysis.text).toLocaleString() },
  ];
  const statBlockW = 31;
  const statGap = 7;
  const statStartX = M + CW - statBlockW * 2 - statGap - 8;
  statItems.forEach((s, i) => {
    const sx = statStartX + i * (statBlockW + statGap);
    doc.setFillColor(248, 250, 252);
    doc.rect(sx, Y + 11, statBlockW, 18, 'F');
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6.5);
    doc.setTextColor(...SLATE_LIGHT);
    doc.text(s.label, sx + 3, Y + 17);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(12);
    doc.setTextColor(15, 23, 42);
    doc.text(s.value, sx + 3, Y + 25);
  });

  Y += scoreCardH + 6;

  // ── Findings by Category bars ─────────────────────────────────────────────────
  drawCard(doc, M, Y, CW, 52);

  const cbInnerL = M + 6;
  const cbInnerT = Y + 5;

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.setTextColor(15, 23, 42);
  doc.text(labels.findingsByCategory, cbInnerL, cbInnerT + 4);

  const severities: Severity[] = ['factually_incorrect', 'potentially_offensive', 'biased', 'outdated'];
  // Count from the filtered set so bars match exactly what is shown on the page
  const maxCount = Math.max(...Object.values(displayCounts), 1);
  const totalCountForPct = Math.max(Object.values(displayCounts).reduce((sum, count) => sum + count, 0), 1);
  const barAreaW = CW - 12 - 48 - 21; // subtract label + count/percent + padding

  severities.forEach((sev, i) => {
    const rowY     = cbInnerT + 11 + i * 9.5;
    const cols     = SEVERITY_COLOR[sev];
    const count    = displayCounts[sev] ?? 0;
    const pct      = Math.round((count / totalCountForPct) * 100);
    const barFill  = (count / maxCount) * barAreaW;

    // Severity label
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(...cols.label);
    doc.text(labels.severity[sev], cbInnerL, rowY + 3.2);

    // Track background
    const bx = cbInnerL + 50;
    doc.setFillColor(233, 228, 248);
    doc.rect(bx, rowY, barAreaW, 3.5, 'F');

    // Fill bar
    if (barFill > 0) {
      doc.setFillColor(...cols.bar);
      doc.rect(bx, rowY, barFill, 3.5, 'F');
    }

    // Count
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.5);
    doc.setTextColor(...SLATE);
    doc.text(`${count} - ${pct}%`, bx + barAreaW + 2.5, rowY + 3.2);
  });

  Y += 52 + 6;

  // ── Section header: Findings ─────────────────────────────────────────────────
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.setTextColor(...PURPLE);
  doc.text(labels.findings, M, Y);

  // Count badge
  const countBadgeX = M + textWidth(doc, labels.findings) + 3;
  pillBadge(doc, countBadgeX, Y, String(totalFindings), PURPLE_LIGHT, [255, 255, 255], 8);

  Y += 7;

  // ── Individual finding cards ─────────────────────────────────────────────────
  const cardMarginBottom = 4;
  const innerPad         = 5;
  const leftBorderW      = 3;
  const textStartX       = M + leftBorderW + innerPad;
  const textW            = CW - leftBorderW - innerPad - 4;

  // Helper to start a fresh page and re-draw background + section header
  function newFindingsPage() {
    doc.addPage();
    drawPageBg(doc, pageWidth, pageHeight);

    // Thin top bar
    doc.setFillColor(...PURPLE);
    doc.rect(0, 0, pageWidth, 1.5, 'F');

    // Running header
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(...PURPLE);
    doc.text(labels.continued, M, 8);

    Y = 14;
  }

  if (displayResults.length === 0) {
    drawCard(doc, M, Y, CW, 20);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.setTextColor(...SLATE);
    doc.text(labels.noFindings, M + 6, Y + 12);
    Y += 24;
  }

  for (const [idx, result] of displayResults.entries()) {
    const cols = SEVERITY_COLOR[result.severity] ?? SEVERITY_COLOR.outdated;

    // Compute card height
    doc.setFont('times', 'normal');
    doc.setFontSize(8.5);
    const expLines  = splitLines(doc, result.explanation || '', textW);
    const suggLines = result.suggestion
      ? splitLines(doc, `${labels.suggestedFix} ${result.suggestion}`, textW)
      : [];

    const cardH =
      innerPad             // top padding
      + 5.5                // phrase line
      + 2.5                // gap
      + expLines.length * 4.5    // explanation
      + (suggLines.length > 0 ? 3 + suggLines.length * 4.5 : 0) // suggestion
      + innerPad;          // bottom padding

    // Page break check
    if (Y + cardH + 2 > pageHeight - 12) {
      newFindingsPage();
    }

    // Card shadow + background
    drawCard(doc, M, Y, CW, cardH);

    // Colored left border
    doc.setFillColor(...cols.border);
    doc.rect(M, Y, leftBorderW, cardH, 'F');

    // Top row: index + phrase
    const phraseY = Y + innerPad + 4;
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7);
    doc.setTextColor(...SLATE_LIGHT);
    doc.text(`#${idx + 1}`, textStartX, phraseY);

    // Badges right-aligned: measure each pill width, then place from right edge leftward
    const BADGE_FS = 7;
    const BADGE_PX = 2.2; // inner horizontal padding used in pillBadge
    function measurePill(text: string): number {
      doc.setFontSize(BADGE_FS);
      return textWidth(doc, text) + BADGE_PX * 2;
    }
    let rightEdge = M + CW - 4;
    const sevText = labels.severity[result.severity];
    const sevPW   = measurePill(sevText);
    pillBadge(doc, rightEdge - sevPW, phraseY, sevText, cols.pill_bg, cols.pill_fg, BADGE_FS);
    rightEdge -= sevPW + 3;
    if (result.category) {
      const catCols = LLM_CAT_COLOR[result.category];
      if (catCols) {
        const catText = labels.category[result.category as keyof typeof labels.category] ?? result.category;
        const catPW = measurePill(catText);
        pillBadge(doc, rightEdge - catPW, phraseY, catText, catCols.pill_bg, catCols.pill_fg, BADGE_FS);
        rightEdge -= catPW + 3;
      }
    }

    const idxW = textWidth(doc, `#${idx + 1}`) + 2;
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9.5);
    doc.setTextColor(15, 23, 42);
    const phraseDisplay = `"${result.phrase}"`;
    const phraseMaxW = Math.max(24, rightEdge - (textStartX + idxW) - 2);
    doc.text(ellipsizeToWidth(doc, phraseDisplay, phraseMaxW), textStartX + idxW, phraseY);

    // Explanation (Times — elegant, formal)
    const expY = phraseY + 3.5;
    doc.setFont('times', 'normal');
    doc.setFontSize(8.5);
    doc.setTextColor(...SLATE);
    expLines.forEach((line, li) => {
      doc.text(line, textStartX, expY + li * 4.5);
    });

    // Suggested fix
    if (suggLines.length > 0) {
      const sugY = expY + expLines.length * 4.5 + 3;
      doc.setFont('times', 'italic');
      doc.setFontSize(8.5);
      doc.setTextColor(...PURPLE_LIGHT);
      suggLines.forEach((line, li) => {
        doc.text(line, textStartX, sugY + li * 4.5);
      });
    }

    Y += cardH + cardMarginBottom;
  }

  // ── Footer on every page ──────────────────────────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const totalPages: number = (doc as any).internal.getNumberOfPages();
  for (let p = 1; p <= totalPages; p++) {
    doc.setPage(p);
    doc.setFontSize(7);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(...SLATE_LIGHT);
    doc.text(labels.watermark, pageWidth / 2, pageHeight - 5, { align: 'center' });
    doc.text(`${p} / ${totalPages}`, pageWidth - M, pageHeight - 5, { align: 'right' });
  }

  // ── Output ────────────────────────────────────────────────────────────────────
  if (options.returnBase64) return doc.output('datauristring');
  const safe = (options.fileName || 'analysis').replace(/[^a-z0-9_\-]/gi, '_');
  doc.save(`${safe}_inclusify_report.pdf`);
}
