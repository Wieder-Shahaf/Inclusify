'use client';

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import IssueTooltip from './IssueTooltip';
import { Annotation } from './AnnotatedText';
import type { BboxAnnotation, PageSize } from '@/lib/api/client';
import type { Severity } from './SeverityBadge';
import { ChevronLeft, ChevronRight, Search } from 'lucide-react';
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

// ── PDF viewer with text-layer phrase injection ──────────────────────────────
const PDF_RENDER_WIDTH = 680;

const HIGHLIGHT_COLORS: Record<Severity, string> = {
  outdated: 'background:rgba(186,230,253,0.85);border-bottom:2px solid #0ea5e9;border-radius:2px;',
  biased: 'background:rgba(253,230,138,0.85);border-bottom:2px solid #f59e0b;border-radius:2px;',
  potentially_offensive: 'background:rgba(254,205,211,0.85);border-bottom:2px solid #f43f5e;border-radius:2px;',
  factually_incorrect: 'background:rgba(254,202,202,0.85);border-bottom:2px solid #ef4444;border-radius:2px;',
};

function PdfViewer({
  file,
  annotations,
  onAnnotationClick,
  activeFinding,
}: {
  file: File;
  annotations: Annotation[];
  onAnnotationClick: (ann: Annotation) => void;
  activeFinding?: { phrase: string; severity: Severity } | null;
}) {
  const pdf = usePdfLib();
  const [numPages, setNumPages] = useState(0);
  const [displayPage, setDisplayPage] = useState(1);
  const [pageInput, setPageInput] = useState('1');
  const [searchQuery, setSearchQuery] = useState('');
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [portals, setPortals] = useState<Array<{ el: HTMLElement; annotation: Annotation; rawPhrase: string }>>([]);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const injectedPages = useRef<Set<number>>(new Set());
  const prevHighlightRef = useRef<HTMLSpanElement | null>(null);

  const scrollToPage = useCallback((pageNo: number) => {
    const el = pageRefs.current.get(pageNo);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  const findAndHighlight = useCallback((phrase: string, severity: Severity) => {
    // Remove previous highlight
    if (prevHighlightRef.current) {
      const prev = prevHighlightRef.current;
      const parent = prev.parentNode;
      if (parent) {
        const textNode = document.createTextNode(prev.textContent ?? '');
        parent.replaceChild(textNode, prev);
      }
      prevHighlightRef.current = null;
    }
    if (!phrase) return;
    const lowerPhrase = phrase.toLowerCase();
    const style = HIGHLIGHT_COLORS[severity] ?? HIGHLIGHT_COLORS.biased;

    for (const [, pageEl] of pageRefs.current) {
      const textLayer = pageEl.querySelector('.react-pdf__Page__textContent');
      if (!textLayer) continue;
      const walker = document.createTreeWalker(textLayer, NodeFilter.SHOW_TEXT);
      let node: Node | null;
      while ((node = walker.nextNode())) {
        const text = node.nodeValue ?? '';
        const pos = text.toLowerCase().indexOf(lowerPhrase);
        if (pos === -1) continue;
        const parent = node.parentNode;
        if (!parent) continue;
        const before = text.slice(0, pos);
        const matched = text.slice(pos, pos + phrase.length);
        const after = text.slice(pos + phrase.length);
        const span = document.createElement('span');
        span.setAttribute('style', style + 'cursor:pointer;');
        span.textContent = matched;
        node.nodeValue = before;
        node.parentNode!.insertBefore(span, node.nextSibling);
        if (after) node.parentNode!.insertBefore(document.createTextNode(after), span.nextSibling);
        prevHighlightRef.current = span;
        span.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
    }
  }, []);

  useEffect(() => {
    if (activeFinding) findAndHighlight(activeFinding.phrase, activeFinding.severity);
  }, [activeFinding, findAndHighlight]);

  const handleSearch = useCallback(() => {
    if (searchQuery.trim()) findAndHighlight(searchQuery.trim(), 'biased');
  }, [searchQuery, findAndHighlight]);

  const phrases = useMemo(
    () => annotations.map(ann => ({ phrase: ann.label, annotation: ann })),
    [annotations],
  );

  useEffect(() => {
    const url = URL.createObjectURL(file);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setFileUrl(url);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPortals([]);
    pageRefs.current.clear();
    injectedPages.current.clear();
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const makeTextLayerHandler = useCallback(
    (pageNumber: number) => () => {
      if (injectedPages.current.has(pageNumber)) return;
      injectedPages.current.add(pageNumber);

      const pageEl = pageRefs.current.get(pageNumber);
      if (!pageEl) return;

      const textLayer = pageEl.querySelector('.react-pdf__Page__textContent');
      if (!textLayer) return;

      const walker = document.createTreeWalker(textLayer, NodeFilter.SHOW_TEXT);
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

      if (newPortals.length > 0) {
        setPortals(prev => [...prev, ...newPortals]);
      }
    },
    [phrases],
  );

  if (!pdf || !fileUrl) {
    return (
      <div className="flex items-center justify-center h-32 text-slate-400 text-sm">
        Loading PDF viewer…
      </div>
    );
  }

  const { Document, Page } = pdf;

  return (
    <div className="flex flex-col">
      {/* Navigation toolbar */}
      {numPages > 0 && (
        <div className="sticky top-0 z-10 flex items-center gap-2 px-3 py-2 mb-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-sm text-xs">
          <button
            onClick={() => { const p = Math.max(1, displayPage - 1); setDisplayPage(p); setPageInput(String(p)); scrollToPage(p); }}
            disabled={displayPage <= 1}
            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-slate-500">Page</span>
          <input
            type="number"
            min={1}
            max={numPages}
            value={pageInput}
            onChange={e => setPageInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') {
                const p = Math.min(numPages, Math.max(1, parseInt(pageInput) || 1));
                setDisplayPage(p); scrollToPage(p);
              }
            }}
            className="w-12 text-center border border-slate-300 dark:border-slate-600 rounded px-1 py-0.5 bg-white dark:bg-slate-800 text-xs"
          />
          <span className="text-slate-500">of {numPages}</span>
          <button
            onClick={() => { const p = Math.min(numPages, displayPage + 1); setDisplayPage(p); setPageInput(String(p)); scrollToPage(p); }}
            disabled={displayPage >= numPages}
            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <div className="ml-auto flex items-center gap-1">
            <Search className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              className="w-28 border border-slate-300 dark:border-slate-600 rounded px-2 py-0.5 bg-white dark:bg-slate-800 text-xs placeholder:text-slate-400"
            />
          </div>
        </div>
      )}
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
          return (
            <div
              key={pageNo}
              ref={(el) => {
                if (el) pageRefs.current.set(pageNo, el);
                else pageRefs.current.delete(pageNo);
              }}
              className="relative mb-4 shadow-md mx-auto"
              style={{ width: PDF_RENDER_WIDTH, display: 'block' }}
            >
              <Page
                pageNumber={pageNo}
                width={PDF_RENDER_WIDTH}
                renderTextLayer={true}
                renderAnnotationLayer={false}
                onRenderTextLayerSuccess={makeTextLayerHandler(pageNo)}
              />
            </div>
          );
        })}
      </Document>
      {portals.map((p, idx) =>
        createPortal(
          <IssueTooltip
            annotation={p.annotation}
            onOpenSidePanel={() => onAnnotationClick(p.annotation)}
          >
            {p.rawPhrase}
          </IssueTooltip>,
          p.el,
          `pdf-portal-${idx}`,
        ),
      )}
    </div>
  );
}

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

        // Collect all text nodes first, then process in reverse so DOM mutations
        // to later nodes don't invalidate earlier positions in the list.
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
  activeFinding?: { phrase: string; severity: Severity } | null;
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
  activeFinding,
}: DocumentViewerProps) {
  if (inputType === 'pdf' && uploadedFile) {
    return (
      <PdfViewer
        file={uploadedFile}
        annotations={annotations}
        onAnnotationClick={onAnnotationClick}
        activeFinding={activeFinding}
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
}
