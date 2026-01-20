'use client';

import { Annotation } from './AnnotatedText';
import SeverityBadge from './SeverityBadge';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';

type AnnotationSidePanelProps = {
  annotation: Annotation | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export default function AnnotationSidePanel({
  annotation,
  open,
  onOpenChange,
}: AnnotationSidePanelProps) {
  if (!annotation) return null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <span>{annotation.label}</span>
            <SeverityBadge level={annotation.severity} />
          </SheetTitle>
          <SheetDescription>
            Details about this issue
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-4">
          {annotation.explanation && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Why is this problematic?</h3>
              <p className="text-sm text-slate-600 dark:text-slate-300">{annotation.explanation}</p>
            </div>
          )}
          {annotation.suggestion && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Suggested replacement</h3>
              <code className="px-3 py-2 bg-slate-100 dark:bg-slate-800 rounded text-sm block">
                {annotation.suggestion}
              </code>
            </div>
          )}
          {annotation.references && annotation.references.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-2">Learn more</h3>
              <ul className="space-y-2">
                {annotation.references.map((ref, i) => (
                  <li key={i}>
                    <a
                      href={ref.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm text-pride-purple hover:underline"
                    >
                      {ref.label} →
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
