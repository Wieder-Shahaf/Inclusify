'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import IssueTooltip from './IssueTooltip';
import { Annotation } from './AnnotatedText';
import type { BboxAnnotation, PageSize } from '@/lib/api/client';

// ── Severity colours for PDF bbox overlays ──────────────────────────────────
const SEV_FILL: Record<string, string> = {
  outdated: 'rgba(14,165,233,0.2)',
  biased: 'rgba(245,158,11,0.2)',
  potentially_offensive: 'rgba(244,63,94,0.2)',
  factually_incorrect: 'rgba(239,68,68,0.2)',
};
const SEV_BORDER: Record<string, string> = {
  outdated: 'rgb(14,165,233)',
  biased: 'rgb(245,158,11)',
  potentially_offensive: 'rgb(244,63,94)',
  factually_incorrect: 'rgb(239,68,68)',
};

// ── react-pdf: loaded lazily to avoid SSR errors ────────────────────────────
let pdfLib: typeof import('react-pdf') | null = null;

function usePdfLib() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (pdfLib) { setReady(true); return; }
    import('react-pdf').then((mod) => {
      mod.pdfjs.GlobalWorkerOptions.workerSrc =
        `//unpkg.com/pdfjs-dist@${mod.pdfjs.version}/build/pdf.worker.min.mjs`;
      pdfLib = mod;
      setReady(true);
    });
  }, []);
  return ready ? pdfLib : null;
}

// ── Plain-text view with offset-based highlights ─────────────────────────────
function AnnotatedPlainText({
  text,
  annotations,
  onAnnotationClick,
}: {
  text: string;
  annotations: Annotation[];
  onAnnotationClick: (ann: Annotation) => void;
}) {
  if (!text) return null;

  const sorted = [...annotations].sort((a, b) => a.start - b.start);
  const nonOverlapping: Annotation[] = [];
  let lastEnd = -1;
  for (const ann of sorted) {
    if (ann.start >= lastEnd) {
      nonOverlapping.push(ann);
      lastEnd = ann.end;
    }
  }

  const parts: Array<{ content: string; annotation?: Annotation }> = [];
  let cursor = 0;
  for (const ann of nonOverlapping) {
    if (ann.start > cursor) parts.push({ content: text.slice(cursor, ann.start) });
    parts.push({ content: text.slice(ann.start, ann.end), annotation: ann });
    cursor = ann.end;
  }
  if (cursor < text.length) parts.push({ content: text.slice(cursor) });

  return (
    <span className="whitespace-pre-wrap leading-8">
      {parts.map((part, idx) =>
        part.annotation ? (
          <span key={idx} id={`ann-${part.annotation.start}`}>
            <IssueTooltip
              annotation={part.annotation}
              onOpenSidePanel={() => onAnnotationClick(part.annotation!)}
            >
              {part.content}
            </IssueTooltip>
          </span>
        ) : (
          <span key={idx}>{part.content}</span>
        )
      )}
    </span>
  );
}

// ── Split a plain string at flagged phrases and wrap with IssueTooltip ───────
function annotateString(
  text: string,
  phrases: Array<{ phrase: string; annotation: Annotation }>,
  onAnnotationClick: (ann: Annotation) => void,
  keyPrefix: string,
): React.ReactNode[] {
  if (!phrases.length) return [<span key={keyPrefix}>{text}</span>];

  const nodes: React.ReactNode[] = [];
  let remaining = text;
  let offset = 0;

  while (remaining.length > 0) {
    let earliest: { index: number; length: number; annotation: Annotation } | null = null;
    for (const { phrase, annotation } of phrases) {
      if (!phrase) continue;
      const idx = remaining.toLowerCase().indexOf(phrase.toLowerCase());
      if (idx !== -1 && (earliest === null || idx < earliest.index)) {
        earliest = { index: idx, length: phrase.length, annotation };
      }
    }

    if (!earliest) {
      nodes.push(<span key={`${keyPrefix}-t${offset}`}>{remaining}</span>);
      break;
    }

    if (earliest.index > 0) {
      nodes.push(
        <span key={`${keyPrefix}-p${offset}`}>{remaining.slice(0, earliest.index)}</span>,
      );
    }

    const matched = remaining.slice(earliest.index, earliest.index + earliest.length);
    const ann = earliest.annotation;
    nodes.push(
      <span key={`${keyPrefix}-a${offset + earliest.index}`} id={`ann-${ann.start}`}>
        <IssueTooltip annotation={ann} onOpenSidePanel={() => onAnnotationClick(ann)}>
          {matched}
        </IssueTooltip>
      </span>,
    );

    offset += earliest.index + earliest.length;
    remaining = remaining.slice(earliest.index + earliest.length);
  }

  return nodes;
}

// ── Markdown viewer (PPTX / DOCX) with phrase-matching highlights ────────────
function MarkdownViewer({
  markdownText,
  annotations,
  onAnnotationClick,
  isHebrew,
}: {
  markdownText: string;
  annotations: Annotation[];
  onAnnotationClick: (ann: Annotation) => void;
  isHebrew: boolean;
}) {
  const phrases = useMemo(
    () => annotations.map((ann) => ({ phrase: ann.label, annotation: ann })),
    [annotations],
  );

  const annotate = useCallback(
    (children: React.ReactNode, key: string): React.ReactNode => {
      if (typeof children === 'string') {
        return annotateString(children, phrases, onAnnotationClick, key);
      }
      if (Array.isArray(children)) {
        return children.flatMap((child, i) =>
          typeof child === 'string'
            ? annotateString(child, phrases, onAnnotationClick, `${key}-${i}`)
            : [child],
        );
      }
      return children;
    },
    [phrases, onAnnotationClick],
  );

  const components = useMemo(
    () => ({
      h1: ({ children }: { children?: React.ReactNode }) => (
        <h1 className="text-2xl font-bold mt-6 mb-3 text-slate-800 dark:text-white">
          {annotate(children, 'h1')}
        </h1>
      ),
      h2: ({ children }: { children?: React.ReactNode }) => (
        <h2 className="text-xl font-semibold mt-5 mb-2 text-slate-700 dark:text-slate-100">
          {annotate(children, 'h2')}
        </h2>
      ),
      h3: ({ children }: { children?: React.ReactNode }) => (
        <h3 className="text-lg font-semibold mt-4 mb-2 text-slate-700 dark:text-slate-200">
          {annotate(children, 'h3')}
        </h3>
      ),
      p: ({ children }: { children?: React.ReactNode }) => (
        <p className="mb-3 leading-7 text-slate-700 dark:text-slate-200">
          {annotate(children, 'p')}
        </p>
      ),
      li: ({ children }: { children?: React.ReactNode }) => (
        <li className="mb-1 leading-7 text-slate-700 dark:text-slate-200">
          {annotate(children, 'li')}
        </li>
      ),
      ul: ({ children }: { children?: React.ReactNode }) => (
        <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>
      ),
      ol: ({ children }: { children?: React.ReactNode }) => (
        <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>
      ),
      strong: ({ children }: { children?: React.ReactNode }) => (
        <strong className="font-semibold">{annotate(children, 'strong')}</strong>
      ),
      em: ({ children }: { children?: React.ReactNode }) => (
        <em className="italic">{annotate(children, 'em')}</em>
      ),
      table: ({ children }: { children?: React.ReactNode }) => (
        <div className="overflow-x-auto mb-3">
          <table className="w-full text-sm border-collapse">{children}</table>
        </div>
      ),
      th: ({ children }: { children?: React.ReactNode }) => (
        <th className="border border-slate-300 dark:border-slate-600 px-3 py-2 bg-slate-100 dark:bg-slate-800 font-semibold text-left">
          {annotate(children, 'th')}
        </th>
      ),
      td: ({ children }: { children?: React.ReactNode }) => (
        <td className="border border-slate-300 dark:border-slate-600 px-3 py-2">
          {annotate(children, 'td')}
        </td>
      ),
    }),
    [annotate],
  );

  return (
    <div dir={isHebrew ? 'rtl' : 'ltr'}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components as never}>
        {markdownText}
      </ReactMarkdown>
    </div>
  );
}

// ── PDF viewer with bbox overlays ────────────────────────────────────────────
const PDF_RENDER_WIDTH = 680;

function PdfViewer({
  file,
  annotations,
  bboxAnnotations,
  pageSizes,
  onAnnotationClick,
}: {
  file: File;
  annotations: Annotation[];
  bboxAnnotations: BboxAnnotation[];
  pageSizes: Record<string, PageSize>;
  onAnnotationClick: (ann: Annotation) => void;
}) {
  const pdf = usePdfLib();
  const [numPages, setNumPages] = useState(0);
  const [fileUrl, setFileUrl] = useState<string | null>(null);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setFileUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // page_no → overlays for that page
  const overlaysByPage = useMemo(() => {
    const map: Record<number, Array<{ bbox: BboxAnnotation['bbox']; annotation: Annotation }>> = {};
    for (const ann of annotations) {
      for (const ba of bboxAnnotations) {
        if (ann.start < ba.end && ann.end > ba.start) {
          (map[ba.page] ??= []).push({ bbox: ba.bbox, annotation: ann });
        }
      }
    }
    return map;
  }, [annotations, bboxAnnotations]);

  if (!pdf || !fileUrl) {
    return (
      <div className="flex items-center justify-center h-32 text-slate-400 text-sm">
        Loading PDF viewer…
      </div>
    );
  }

  const { Document, Page } = pdf;

  return (
    <Document
      file={fileUrl}
      onLoadSuccess={({ numPages: n }) => setNumPages(n)}
      loading={
        <div className="flex items-center justify-center h-32 text-slate-400 text-sm animate-pulse">
          Rendering PDF…
        </div>
      }
      error={
        <div className="flex items-center justify-center h-32 text-slate-400 text-sm">
          Could not render PDF preview.
        </div>
      }
    >
      {Array.from({ length: numPages }, (_, i) => {
        const pageNo = i + 1;
        const ps = pageSizes[String(pageNo)];
        const overlays = overlaysByPage[pageNo] ?? [];

        return (
          <div
            key={pageNo}
            className="relative mb-4 shadow-md mx-auto"
            style={{ width: PDF_RENDER_WIDTH, display: 'block' }}
          >
            <Page
              pageNumber={pageNo}
              width={PDF_RENDER_WIDTH}
              renderTextLayer={false}
              renderAnnotationLayer={false}
            />

            {ps &&
              overlays.map(({ bbox, annotation }, idx) => {
                const scale = PDF_RENDER_WIDTH / ps.width;
                const left = bbox.l * scale;
                // PDF origin is bottom-left; CSS origin is top-left → flip Y
                const top = (ps.height - bbox.t) * scale;
                const width = Math.max((bbox.r - bbox.l) * scale, 4);
                const height = Math.max((bbox.t - bbox.b) * scale, 4);

                return (
                  <div
                    key={`${pageNo}-${idx}`}
                    style={{
                      position: 'absolute',
                      left,
                      top,
                      width,
                      height,
                      backgroundColor: SEV_FILL[annotation.severity] ?? SEV_FILL.biased,
                      border: `1.5px solid ${SEV_BORDER[annotation.severity] ?? SEV_BORDER.biased}`,
                      borderRadius: 2,
                      cursor: 'pointer',
                      zIndex: 10,
                    }}
                    title={annotation.label}
                    onClick={() => onAnnotationClick(annotation)}
                  />
                );
              })}
          </div>
        );
      })}
    </Document>
  );
}

// ── Public component ─────────────────────────────────────────────────────────
export interface DocumentViewerProps {
  inputType: 'pdf' | 'docx' | 'pptx' | 'txt';
  text: string;
  annotations: Annotation[];
  uploadedFile: File | null;
  bboxAnnotations: BboxAnnotation[] | null;
  pageSizes: Record<string, PageSize> | null;
  markdownText: string | null;
  onAnnotationClick: (annotation: Annotation) => void;
  isHebrew: boolean;
}

export default function DocumentViewer({
  inputType,
  text,
  annotations,
  uploadedFile,
  bboxAnnotations,
  pageSizes,
  markdownText,
  onAnnotationClick,
  isHebrew,
}: DocumentViewerProps) {
  if (inputType === 'pdf' && uploadedFile && bboxAnnotations && pageSizes) {
    return (
      <PdfViewer
        file={uploadedFile}
        annotations={annotations}
        bboxAnnotations={bboxAnnotations}
        pageSizes={pageSizes}
        onAnnotationClick={onAnnotationClick}
      />
    );
  }

  if ((inputType === 'pptx' || inputType === 'docx') && markdownText) {
    return (
      <MarkdownViewer
        markdownText={markdownText}
        annotations={annotations}
        onAnnotationClick={onAnnotationClick}
        isHebrew={isHebrew}
      />
    );
  }

  return (
    <AnnotatedPlainText
      text={text}
      annotations={annotations}
      onAnnotationClick={onAnnotationClick}
    />
  );
}
