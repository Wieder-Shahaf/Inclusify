'use client';

import { useState, useEffect, useMemo, useCallback, useRef, forwardRef, useImperativeHandle } from 'react';
import { createPortal } from 'react-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import IssueTooltip, { severityConfig } from './IssueTooltip';
import { Annotation } from './AnnotatedText';
import type { BboxAnnotation, PageSize } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import 'react-pdf/dist/Page/TextLayer.css';

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

// ── PDF viewer: span-rect overlays per page ──────────────────────────────────
const PDF_RENDER_WIDTH = 680;

type PdfOverlay = {
  top: number;
  left: number;
  width: number;
  height: number;
  annotation: Annotation;
};

export interface PdfNavHandle {
  scrollToPage: (n: number) => void;
  /** Returns true if a match was found and scrolled to. */
  handleSearch: (term: string) => boolean;
}

const PdfViewer = forwardRef<PdfNavHandle, {
  file: File;
  annotations: Annotation[];
  onAnnotationClick: (ann: Annotation) => void;
  onNumPagesChange?: (n: number) => void;
  onPageChange?: (n: number) => void;
}>(function PdfViewer({ file, annotations, onAnnotationClick, onNumPagesChange, onPageChange }, ref) {
  const pdf = usePdfLib();
  const [numPages, setNumPages] = useState(0);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageOverlays, setPageOverlays] = useState<Map<number, PdfOverlay[]>>(new Map());

  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const processedPages = useRef<Set<number>>(new Set());
  const pageTextIndex = useRef<Map<number, string>>(new Map());

  const scrollToPage = useCallback((pageNo: number) => {
    const el = pageRefs.current.get(pageNo);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setCurrentPage(pageNo);
    }
  }, []);

  const handleSearch = useCallback((term: string): boolean => {
    if (!term.trim()) return false;
    // Normalize whitespace so Docling-extracted phrases match PDF.js-rendered text
    // (PDF.js may use non-breaking spaces, ligatures, or different spacing).
    const normalize = (s: string) => s.toLowerCase().replace(/[\s ]+/g, ' ').trim();
    const normTerm = normalize(term);

    // Annotation overlay anchor: scroll directly to the highlight element
    const ann = annotations.find(a => normalize(a.label).includes(normTerm));
    if (ann) {
      const el = document.getElementById(`ann-${ann.start}`);
      if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); return true; }
    }

    // General text: find first page whose normalized text contains the term
    for (const [pageNo, pageText] of Array.from(pageTextIndex.current.entries()).sort(([a], [b]) => a - b)) {
      if (normalize(pageText).includes(normTerm)) { scrollToPage(pageNo); return true; }
    }

    // Last resort: page with a matching overlay label
    for (const [pageNo, overlays] of Array.from(pageOverlays.entries()).sort(([a], [b]) => a - b)) {
      if (overlays.some(o => normalize(o.annotation.label).includes(normTerm))) {
        scrollToPage(pageNo);
        return true;
      }
    }

    return false;
  }, [annotations, pageOverlays, scrollToPage]);

  useImperativeHandle(ref, () => ({ scrollToPage, handleSearch }), [scrollToPage, handleSearch]);
  useEffect(() => { onNumPagesChange?.(numPages); }, [numPages, onNumPagesChange]);
  useEffect(() => { onPageChange?.(currentPage); }, [currentPage, onPageChange]);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setFileUrl(url);
    setPageOverlays(new Map());
    pageRefs.current.clear();
    processedPages.current.clear();
    pageTextIndex.current.clear();
  }, [file]);

  useEffect(() => {
    return () => {
      if (fileUrl) URL.revokeObjectURL(fileUrl);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file]);

  const makeTextLayerHandler = useCallback(
    (pageNumber: number) => () => {
      // Guard inside the rAF (not here) so pages whose text layer fires before content
      // is ready can be retried on the next onRenderTextLayerSuccess call.
      const pageEl = pageRefs.current.get(pageNumber);
      if (!pageEl) return;

      // rAF ensures the text layer has been painted and has valid layout rects
      requestAnimationFrame(() => {
        if (processedPages.current.has(pageNumber)) return;

        const textLayer = pageEl.querySelector('.react-pdf__Page__textContent');
        if (!textLayer) return;

        const allSpans = Array.from(textLayer.querySelectorAll('span')) as HTMLElement[];

        // Join with a space so adjacent spans ("contemporary"+"sexual") become searchable
        // as "contemporary sexual". normalize() collapses any double-spaces later.
        const pageText = allSpans.map(s => s.textContent || '').join(' ');
        if (!pageText.trim()) return; // Text layer not ready — allow retry on next render

        // Mark processed only after confirming content so failed pages can be retried
        processedPages.current.add(pageNumber);
        pageTextIndex.current.set(pageNumber, pageText);

        // For overlay creation only use spans that are actually painted.
        // Zero-dimension spans are PDF.js selection-layer artifacts that produce bogus rects.
        const spans = allSpans.filter(s => {
          if (!(s.textContent || '').length) return false;
          const r = s.getBoundingClientRect();
          return r.width > 0 && r.height > 0;
        });
        if (spans.length === 0) return;

        // Build fullText with space separators so multi-word phrases across spans can match.
        // spanMap records each span's start/end in this spaced string.
        let fullText = '';
        const spanMap: Array<{ start: number; end: number; el: HTMLElement }> = [];
        for (const span of spans) {
          const t = span.textContent || '';
          if (fullText) fullText += ' ';
          spanMap.push({ start: fullText.length, end: fullText.length + t.length, el: span });
          fullText += t;
        }

        const normalize = (s: string) => s.toLowerCase().replace(/\s+/g, ' ').trim();
        const lowerFull = normalize(fullText);
        const pageRect = pageEl.getBoundingClientRect();
        const overlays: PdfOverlay[] = [];

        for (const ann of annotations) {
          if (!ann.label) continue;
          // Normalize phrase whitespace to match the space-joined span text
          const lowerPhrase = normalize(ann.label);
          let idx = lowerFull.indexOf(lowerPhrase);
          while (idx !== -1) {
            const phraseEnd = idx + lowerPhrase.length;
            const relevant = spanMap.filter(s => s.end > idx && s.start < phraseEnd);
            if (relevant.length > 0) {
              const rects = relevant.map(s => s.el.getBoundingClientRect());
              const top = Math.min(...rects.map(r => r.top)) - pageRect.top;
              const left = Math.min(...rects.map(r => r.left)) - pageRect.left;
              const width = Math.max(...rects.map(r => r.right)) - Math.min(...rects.map(r => r.left));
              const height = Math.max(...rects.map(r => r.bottom)) - Math.min(...rects.map(r => r.top));
              // Skip degenerate rects — indicates a span with no real painted position
              if (width > 2 && height > 2) {
                overlays.push({ top, left, width, height, annotation: ann });
              }
            }
            idx = lowerFull.indexOf(lowerPhrase, phraseEnd);
          }
        }

        if (overlays.length > 0) {
          setPageOverlays(prev => new Map(prev).set(pageNumber, overlays));
        }
      });
    },
    [annotations],
  );

  // Precompute which overlay on which page gets the scroll-anchor id for each annotation.
  // We assign ann-{start} to the first occurrence across all pages (lowest page, lowest idx).
  const firstOccurrenceKey = useMemo(() => {
    const map = new Map<number, string>(); // annStart → `${pageNo}-${overlayIdx}`
    for (const [pageNo, overlays] of Array.from(pageOverlays.entries()).sort(([a], [b]) => a - b)) {
      overlays.forEach((overlay, i) => {
        if (!map.has(overlay.annotation.start)) {
          map.set(overlay.annotation.start, `${pageNo}-${i}`);
        }
      });
    }
    return map;
  }, [pageOverlays]);

  if (!pdf || !fileUrl) {
    return (
      <div className="flex items-center justify-center h-32 text-slate-400 text-sm">
        Loading PDF viewer…
      </div>
    );
  }

  const { Document, Page } = pdf;

  return (
    <div>
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
          const overlays = pageOverlays.get(pageNo) || [];
          return (
            <div
              key={pageNo}
              ref={(el) => {
                if (el) pageRefs.current.set(pageNo, el);
                else pageRefs.current.delete(pageNo);
              }}
              className="relative mb-4 shadow-md mx-auto"
              style={{ width: PDF_RENDER_WIDTH }}
            >
              <Page
                pageNumber={pageNo}
                width={PDF_RENDER_WIDTH}
                renderTextLayer={true}
                renderAnnotationLayer={false}
                onRenderTextLayerSuccess={makeTextLayerHandler(pageNo)}
              />
              {overlays.map((overlay, idx) => {
                const cfg = severityConfig[overlay.annotation.severity] || severityConfig.biased;
                const isAnchor = firstOccurrenceKey.get(overlay.annotation.start) === `${pageNo}-${idx}`;
                return (
                  <div
                    key={idx}
                    id={isAnchor ? `ann-${overlay.annotation.start}` : undefined}
                    className="absolute pointer-events-auto"
                    style={{
                      top: overlay.top,
                      left: overlay.left,
                      width: Math.max(overlay.width, 10),
                      height: Math.max(overlay.height, 12),
                      zIndex: 5,
                    }}
                  >
                    <IssueTooltip
                      annotation={overlay.annotation}
                      onOpenSidePanel={() => onAnnotationClick(overlay.annotation)}
                      noHighlight
                    >
                      <div
                        className={cn(
                          'w-full h-full rounded-sm cursor-pointer transition-opacity',
                          cfg.highlightColor,
                          'opacity-40 hover:opacity-65',
                        )}
                      />
                    </IssueTooltip>
                  </div>
                );
              })}
            </div>
          );
        })}
      </Document>
    </div>
  );
});

// ── docx-preview: loaded lazily to avoid SSR errors ─────────────────────────
let docxLib: typeof import('docx-preview') | null = null;

function useDocxLib() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (docxLib) { setReady(true); return; }
    import('docx-preview').then((mod) => {
      docxLib = mod;
      setReady(true);
    });
  }, []);
  return ready ? docxLib : null;
}

// ── Find non-overlapping phrase matches in a plain string ─────────────────────
interface PhraseMatch {
  start: number;
  end: number;
  annotation: Annotation;
  rawPhrase: string;
}

function findTextMatches(
  text: string,
  phrases: Array<{ phrase: string; annotation: Annotation }>,
): PhraseMatch[] {
  const lower = text.toLowerCase();
  const all: PhraseMatch[] = [];
  for (const { phrase, annotation } of phrases) {
    if (!phrase) continue;
    const lp = phrase.toLowerCase();
    let idx = 0;
    while (true) {
      const pos = lower.indexOf(lp, idx);
      if (pos === -1) break;
      all.push({ start: pos, end: pos + phrase.length, annotation, rawPhrase: text.slice(pos, pos + phrase.length) });
      idx = pos + phrase.length;
    }
  }
  all.sort((a, b) => a.start - b.start);
  const result: PhraseMatch[] = [];
  let lastEnd = -1;
  for (const m of all) {
    if (m.start >= lastEnd) {
      result.push(m);
      lastEnd = m.end;
    }
  }
  return result;
}

// ── DOCX viewer: docx-preview render + TreeWalker phrase injection ────────────
function DocxViewer({
  file,
  annotations,
  onAnnotationClick,
}: {
  file: File;
  annotations: Annotation[];
  onAnnotationClick: (ann: Annotation) => void;
}) {
  const docx = useDocxLib();
  const containerRef = useRef<HTMLDivElement>(null);
  const [portals, setPortals] = useState<Array<{ el: HTMLElement; annotation: Annotation; rawPhrase: string }>>([]);

  useEffect(() => {
    if (!docx || !containerRef.current || !file) return;
    const container = containerRef.current;
    container.innerHTML = '';
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPortals([]);

    const phrases = annotations.map((ann) => ({ phrase: ann.label, annotation: ann }));

    file
      .arrayBuffer()
      .then((buffer) =>
        docx.renderAsync(buffer as ArrayBuffer, container, undefined, {
          inWrapper: true,
          ignoreWidth: true,
          className: 'docx',
        }),
      )
      .then(() => {
        if (!containerRef.current) return;

        const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
        const nodes: Text[] = [];
        let n: Node | null;
        while ((n = walker.nextNode())) nodes.push(n as Text);

        const newPortals: Array<{ el: HTMLElement; annotation: Annotation; rawPhrase: string }> = [];

        for (let i = nodes.length - 1; i >= 0; i--) {
          const textNode = nodes[i];
          const text = textNode.nodeValue ?? '';
          const matches = findTextMatches(text, phrases);
          if (!matches.length) continue;

          const parent = textNode.parentNode;
          const nextSib = textNode.nextSibling;
          if (!parent) continue;
          parent.removeChild(textNode);

          let cursor = 0;
          for (const match of matches) {
            if (match.start > cursor) {
              parent.insertBefore(document.createTextNode(text.slice(cursor, match.start)), nextSib);
            }
            const span = document.createElement('span');
            span.id = `ann-${match.annotation.start}`;
            parent.insertBefore(span, nextSib);
            newPortals.push({ el: span, annotation: match.annotation, rawPhrase: match.rawPhrase });
            cursor = match.end;
          }
          if (cursor < text.length) {
            parent.insertBefore(document.createTextNode(text.slice(cursor)), nextSib);
          }
        }

        setPortals(newPortals);
      })
      .catch((err) => {
        console.error('DOCX render error:', err);
      });
  }, [docx, file, annotations]);

  if (!docx) {
    return (
      <div className="flex items-center justify-center h-32 text-slate-400 text-sm animate-pulse">
        Loading document viewer…
      </div>
    );
  }

  return (
    <>
      <div ref={containerRef} className="docx-viewer-wrap" />
      {portals.map((p, idx) =>
        createPortal(
          <IssueTooltip
            annotation={p.annotation}
            onOpenSidePanel={() => onAnnotationClick(p.annotation)}
          >
            {p.rawPhrase}
          </IssueTooltip>,
          p.el,
          `docx-portal-${idx}`,
        ),
      )}
    </>
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
  onPdfNumPages?: (n: number) => void;
  onPdfPageChange?: (n: number) => void;
}

const DocumentViewer = forwardRef<PdfNavHandle, DocumentViewerProps>(function DocumentViewer({
  inputType,
  text,
  annotations,
  uploadedFile,
  bboxAnnotations: _bboxAnnotations,
  pageSizes: _pageSizes,
  markdownText,
  onAnnotationClick,
  isHebrew,
  onPdfNumPages,
  onPdfPageChange,
}, ref) {
  if (inputType === 'pdf' && uploadedFile) {
    return (
      <PdfViewer
        ref={ref}
        file={uploadedFile}
        annotations={annotations}
        onAnnotationClick={onAnnotationClick}
        onNumPagesChange={onPdfNumPages}
        onPageChange={onPdfPageChange}
      />
    );
  }

  if (inputType === 'docx' && uploadedFile) {
    return (
      <DocxViewer
        file={uploadedFile}
        annotations={annotations}
        onAnnotationClick={onAnnotationClick}
      />
    );
  }

  if (inputType === 'pptx' && markdownText) {
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
});

export default DocumentViewer;
