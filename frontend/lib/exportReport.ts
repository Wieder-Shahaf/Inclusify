import type { Annotation } from '@/components/AnnotatedText';
import type { Severity } from '@/components/SeverityBadge';

interface AnalysisData {
  text: string;
  annotations: Annotation[];
  counts: Record<Severity, number>;
  summary: {
    totalIssues: number;
    score: number;
    recommendations: string[];
  };
}

interface ExportOptions {
  fileName: string;
  locale?: string;
  returnBase64?: boolean; // when true, return data URI string instead of triggering browser download
}

export async function exportReport(
  analysis: AnalysisData,
  options: ExportOptions
): Promise<string | void> {
  const { jsPDF } = await import('jspdf');
  const { default: autoTable } = await import('jspdf-autotable');

  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();

  // ── Header ────────────────────────────────────────────────────────────────
  doc.setFillColor(88, 28, 135);
  doc.rect(0, 0, pageWidth, 22, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFontSize(18);
  doc.setFont('helvetica', 'bold');
  doc.text('INCLUSIFY', 14, 14);

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text('LGBTQ+ Inclusive Language Analysis Report', pageWidth / 2, 14, { align: 'center' });
  doc.text(new Date().toLocaleDateString('en-GB'), pageWidth - 14, 14, { align: 'right' });

  // ── Document title ─────────────────────────────────────────────────────────
  doc.setTextColor(30, 30, 30);
  doc.setFontSize(13);
  doc.setFont('helvetica', 'bold');
  doc.text(options.fileName || 'Document Analysis', 14, 32);

  // ── Score summary ──────────────────────────────────────────────────────────
  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(80, 80, 80);
  const score = analysis.summary.score;
  const totalIssues = analysis.summary.totalIssues;

  doc.text(`LGBTQ+ inclusivity score: ${score}/100`, 14, 42);
  doc.text(`Total issues found: ${totalIssues}`, 14, 48);
  doc.text(
    `Outdated: ${analysis.counts.outdated}  |  Biased: ${analysis.counts.biased}  |  Potentially Offensive: ${analysis.counts.potentially_offensive}  |  Factually Incorrect: ${analysis.counts.factually_incorrect}`,
    14,
    54,
  );

  // ── Issues table ───────────────────────────────────────────────────────────
  const rows = analysis.annotations.map((ann) => [
    ann.label,
    ann.severity.replace(/_/g, ' '),
    ann.explanation || '',
    ann.suggestion || '',
    ann.inclusive_sentence || '',
  ]);

  autoTable(doc, {
    startY: 62,
    head: [['Flagged Term', 'Severity', 'Explanation', 'Suggestion', 'Inclusive Version']],
    body: rows,
    styles: { fontSize: 8, cellPadding: 3, overflow: 'linebreak' },
    headStyles: { fillColor: [88, 28, 135], textColor: 255, fontStyle: 'bold' },
    columnStyles: {
      0: { cellWidth: 28 },
      1: { cellWidth: 24 },
      2: { cellWidth: 48 },
      3: { cellWidth: 40 },
      4: { cellWidth: 40 },
    },
    alternateRowStyles: { fillColor: [248, 245, 255] },
    margin: { left: 14, right: 14 },
  });

  // ── Footer watermark on every page ────────────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const totalPages: number = (doc as any).internal.getNumberOfPages();
  const watermarkText =
    options.locale === 'he'
      ? 'ארגון אחווה להט״ב הסטודנטיאלי'
      : 'Achva LGBTQ+ Studential Organization';
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(150, 150, 150);
    doc.text(watermarkText, pageWidth / 2, pageHeight - 8, { align: 'center' });
  }

  // ── Save or return base64 ──────────────────────────────────────────────────
  if (options.returnBase64) {
    return doc.output('datauristring'); // returns 'data:application/pdf;base64,...'
  }
  const safeFileName = (options.fileName || 'analysis').replace(/[^a-z0-9_\-]/gi, '_');
  doc.save(`${safeFileName}_inclusify_report.pdf`);
}
