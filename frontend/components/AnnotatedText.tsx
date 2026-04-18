'use client';

import SeverityBadge, { Severity } from './SeverityBadge';
import { cn } from '@/lib/utils';

export type Annotation = {
  start: number;
  end: number;
  severity: Severity;
  label: string;
  suggestion?: string;
  inclusive_sentence?: string;
  explanation?: string;
  confidence?: number;
  references?: Array<{ label: string; url: string }>;
};

type AnnotatedTextProps = {
  text: string;
  annotations: Annotation[];
  onAnnotationClick?: (annotation: Annotation) => void;
};

export default function AnnotatedText({ text, annotations, onAnnotationClick }: AnnotatedTextProps) {
  if (!text) return null;

  const parts: Array<{ content: string; ann?: Annotation }> = [];
  let cursor = 0;
  const sorted = [...annotations].sort((a, b) => a.start - b.start);

  for (const ann of sorted) {
    if (ann.start > cursor) {
      parts.push({ content: text.slice(cursor, ann.start) });
    }
    parts.push({ content: text.slice(ann.start, ann.end), ann });
    cursor = ann.end;
  }
  if (cursor < text.length) {
    parts.push({ content: text.slice(cursor) });
  }

  const handleClick = (ann: Annotation) => {
    onAnnotationClick?.(ann);
  };

  return (
    <>
      <div className="prose max-w-none dark:prose-invert">
        <p className="leading-7">
          {parts.map((part, idx) =>
            part.ann ? (
              <mark
                key={idx}
                onClick={() => handleClick(part.ann!)}
                className={cn(
                  "rounded-md px-1.5 py-0.5 mx-0.5 bg-gradient-to-r from-pride-purple/20 via-pride-pink/20 to-pride-blue/20 ring-1 ring-pride-purple/20 dark:ring-white/10 cursor-pointer hover:ring-2 hover:ring-pride-purple/40 transition-all"
                )}
                title={`${part.ann.label}${part.ann.suggestion ? ` → ${part.ann.suggestion}` : ''}`}
              >
                {part.content}
              </mark>
            ) : (
              <span key={idx}>{part.content}</span>
            )
          )}
        </p>
        {annotations.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-2">
            {sorted.map((a, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-2 rounded-md bg-slate-900/5 dark:bg-white/5 px-2.5 py-1.5 text-xs"
              >
                <SeverityBadge level={a.severity} />
                <span className="opacity-80">{a.label}</span>
                {a.suggestion && <span className="opacity-60">→ {a.suggestion}</span>}
              </span>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
