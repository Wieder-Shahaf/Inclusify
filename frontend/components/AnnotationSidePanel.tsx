'use client';

import { motion } from 'framer-motion';
import { Annotation } from './AnnotatedText';
import SeverityBadge from './SeverityBadge';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  BookOpen,
  CheckCircle2,
  ExternalLink,
  Lightbulb,
  Quote,
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  Lock,
  AlertTriangle,
  Clock,
  Scale,
  XCircle,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { submitFeedback } from '@/lib/api/client';
import { cn } from '@/lib/utils';

type AnnotationSidePanelProps = {
  annotation: Annotation | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  locale?: string;
  isPrivate?: boolean;
  runId?: string;
};

const severityInfo = {
  outdated: {
    Icon: Clock,
    title: { en: 'Outdated Terminology', he: 'מינוח מיושן' },
    color: 'from-sky-500 to-sky-600',
    iconColor: 'text-sky-500',
    bgLight: 'bg-sky-50 dark:bg-sky-900/20',
    borderColor: 'border-sky-200 dark:border-sky-800',
  },
  biased: {
    Icon: Scale,
    title: { en: 'Biased Language', he: 'שפה מוטה' },
    color: 'from-amber-500 to-amber-600',
    iconColor: 'text-amber-500',
    bgLight: 'bg-amber-50 dark:bg-amber-900/20',
    borderColor: 'border-amber-200 dark:border-amber-800',
  },
  potentially_offensive: {
    Icon: AlertTriangle,
    title: { en: 'Potentially Offensive', he: 'עלול לפגוע' },
    color: 'from-rose-500 to-rose-600',
    iconColor: 'text-rose-500',
    bgLight: 'bg-rose-50 dark:bg-rose-900/20',
    borderColor: 'border-rose-200 dark:border-rose-800',
  },
  factually_incorrect: {
    Icon: XCircle,
    title: { en: 'Factually Incorrect', he: 'שגוי עובדתית' },
    color: 'from-red-500 to-red-600',
    iconColor: 'text-red-500',
    bgLight: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-red-200 dark:border-red-800',
  },
};

export default function AnnotationSidePanel({
  annotation,
  open,
  onOpenChange,
  locale = 'en',
  isPrivate = false,
  runId,
}: AnnotationSidePanelProps) {
  const [copied, setCopied] = useState(false);
  const [vote, setVote] = useState<'up' | 'down' | null>(null);
  const [inclusiveExpanded, setInclusiveExpanded] = useState(false);

  const hasHebrew = (s?: string) => !!s && /[֐-׿]/.test(s);
  const isHe =
    locale === 'he' ||
    hasHebrew(annotation?.label) ||
    hasHebrew(annotation?.explanation);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setVote(null);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setInclusiveExpanded(false);
  }, [annotation?.start, annotation?.end]);

  if (!annotation) return null;

  const info = severityInfo[annotation.severity] || severityInfo.biased;
  const { Icon } = info;

  const t = {
    flaggedTerm:       isHe ? 'מונח מסומן'               : 'Flagged Term',
    whyProblematic:    isHe ? 'מדוע זה בעייתי?'          : 'Why problematic',
    modelConfidence:   isHe ? 'ביטחון המודל'              : 'Confidence',
    suggestedAlt:      isHe ? 'חלופה מומלצת'              : 'Suggested Alternative',
    copySuggestion:    isHe ? 'העתק הצעה'                 : 'Copy',
    copied:            isHe ? '!הועתק'                    : 'Copied!',
    inclusiveVersion:  isHe ? 'גרסה מכלילה'               : 'Inclusive Version',
    learnMore:         isHe ? 'למידע נוסף'                 : 'References',
    closePanel:        isHe ? 'סגור'                      : 'Close',
    feedbackQuestion:  isHe ? 'האם הדגל הזה מועיל?'      : 'Was this flag helpful?',
    voteUp:            isHe ? 'כן'                        : 'Yes',
    voteDown:          isHe ? 'לא'                        : 'No',
    feedbackThanks:    isHe ? 'תודה!'                     : 'Thanks for the feedback!',
    privateNoFeedback: isHe ? 'משוב אינו זמין במצב פרטי' : 'Feedback unavailable in private mode',
  };

  const handleVote = (v: 'up' | 'down') => {
    if (vote !== null) return;
    setVote(v);
    submitFeedback({
      vote: v,
      flaggedText: annotation.label,
      severity: annotation.severity,
      startIdx: annotation.start,
      endIdx: annotation.end,
      findingId: annotation.finding_id,
      runId,
    });
  };

  const handleCopySuggestion = async () => {
    if (annotation.suggestion) {
      await navigator.clipboard.writeText(annotation.suggestion);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        className="w-full sm:max-w-sm p-0 overflow-hidden flex flex-col"
        dir={isHe ? 'rtl' : 'ltr'}
      >
        {/* Compact header */}
        <div className={cn('relative overflow-hidden border-b border-slate-100 dark:border-slate-800')}>
          <div className={cn('absolute inset-0 bg-gradient-to-br opacity-[0.06]', info.color)} />
          <SheetHeader className={cn('relative px-5 py-4', isHe ? 'text-right' : 'text-left')}>
            <div className={cn('flex items-center gap-2.5', isHe && 'flex-row-reverse')}>
              <Icon className={cn('w-4 h-4 shrink-0', info.iconColor)} />
              <div className={cn('flex flex-col gap-0.5', isHe && 'items-end')}>
                <SheetTitle className={cn('text-sm font-semibold text-slate-700 dark:text-slate-200', isHe ? 'text-right' : 'text-left')}>
                  {info.title[isHe ? 'he' : 'en']}
                </SheetTitle>
                {annotation.category && (
                  <span className="text-[11px] text-slate-400 dark:text-slate-500">
                    {annotation.category}
                  </span>
                )}
              </div>
              <div className={cn('ml-auto', isHe && 'ml-0 mr-auto')}>
                <SeverityBadge level={annotation.severity} />
              </div>
            </div>
          </SheetHeader>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          <div className="space-y-4">

            {/* Flagged Term */}
            <div className={cn('px-3 py-2.5 rounded-lg border', info.bgLight, info.borderColor)}>
              <div className={cn('flex items-center gap-1.5 mb-1', isHe && 'flex-row-reverse')}>
                <Quote className="w-3 h-3 text-slate-400" />
                <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">
                  {t.flaggedTerm}
                </span>
              </div>
              <p className={cn('text-sm font-semibold text-slate-800 dark:text-white', isHe && 'text-right')}>
                &ldquo;{annotation.label}&rdquo;
              </p>
            </div>

            {/* Explanation */}
            {annotation.explanation && (
              <div>
                <div className={cn('flex items-center gap-1.5 mb-1.5', isHe && 'flex-row-reverse')}>
                  <Lightbulb className="w-3.5 h-3.5 text-pride-purple" />
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">
                    {t.whyProblematic}
                  </span>
                </div>
                <p className={cn('text-xs text-slate-600 dark:text-slate-300 leading-relaxed', isHe && 'text-right')}>
                  {annotation.explanation}
                </p>
              </div>
            )}

            {/* Confidence */}
            <div className={cn('flex items-center gap-3', isHe && 'flex-row-reverse')}>
              <span className="text-[11px] text-slate-400 dark:text-slate-500 shrink-0">{t.modelConfidence}</span>
              {annotation.confidence != null ? (
                <>
                  <div className="flex-1 h-1 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-pride-purple/60"
                      style={{ width: `${annotation.confidence * 100}%` }}
                    />
                  </div>
                  <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400 tabular-nums shrink-0">
                    {Math.round(annotation.confidence * 100)}%
                  </span>
                </>
              ) : (
                <span className="text-[11px] text-slate-300 dark:text-slate-600 shrink-0">—</span>
              )}
            </div>

            {/* Suggested Alternative — green card style, collapsible for long text */}
            {annotation.suggestion && (
              <div>
                <div className={cn('flex items-center gap-1.5 mb-1.5', isHe && 'flex-row-reverse')}>
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">
                    {t.suggestedAlt}
                  </span>
                </div>
                <div className="relative px-3 py-2.5 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                  <p className={cn(
                    'text-xs text-green-800 dark:text-green-200 leading-relaxed',
                    isHe ? 'pl-0 pr-7 text-right' : 'pr-7',
                    !inclusiveExpanded && 'line-clamp-3',
                  )}>
                    {annotation.suggestion}
                  </p>
                  {annotation.suggestion.length > 160 && (
                    <button
                      onClick={() => setInclusiveExpanded(e => !e)}
                      className="mt-1.5 text-[11px] text-green-700 dark:text-green-400 font-medium hover:underline"
                    >
                      {inclusiveExpanded ? 'Show less' : 'Show more'}
                    </button>
                  )}
                  <button
                    onClick={handleCopySuggestion}
                    className={cn(
                      'absolute top-2 p-1.5 rounded-md hover:bg-green-100 dark:hover:bg-green-800/40 transition-colors',
                      isHe ? 'left-2' : 'right-2'
                    )}
                    title={t.copySuggestion}
                  >
                    {copied
                      ? <Check className="w-3.5 h-3.5 text-green-600" />
                      : <Copy className="w-3.5 h-3.5 text-green-400" />
                    }
                  </button>
                </div>
                {copied && (
                  <p className="text-[11px] text-green-500 mt-1 text-center">{t.copied}</p>
                )}
              </div>
            )}

            {/* References */}
            {annotation.references && annotation.references.length > 0 && (
              <div>
                <div className={cn('flex items-center gap-1.5 mb-1.5', isHe && 'flex-row-reverse')}>
                  <BookOpen className="w-3.5 h-3.5 text-pride-purple" />
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">
                    {t.learnMore}
                  </span>
                </div>
                <div className="space-y-1.5">
                  {annotation.references.map((ref, i) => (
                    <a
                      key={i}
                      href={ref.url}
                      target="_blank"
                      rel="noreferrer"
                      className={cn(
                        'flex items-center gap-2.5 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700',
                        'hover:border-pride-purple/40 hover:bg-pride-purple/5 transition-all group',
                        isHe && 'flex-row-reverse'
                      )}
                    >
                      <ExternalLink className="w-3.5 h-3.5 text-slate-400 group-hover:text-pride-purple transition-colors shrink-0" />
                      <div className={cn('flex-1 min-w-0', isHe && 'text-right')}>
                        <p className="text-xs font-medium text-slate-700 dark:text-slate-200 group-hover:text-pride-purple transition-colors truncate">
                          {ref.label}
                        </p>
                        <p className="text-[10px] text-slate-400 truncate">{new URL(ref.url).hostname}</p>
                      </div>
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Feedback */}
        <div className="px-5 pb-3 shrink-0">
          <div className={cn(
            'rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-2.5',
            'bg-slate-50 dark:bg-slate-800/50',
          )}>
            {isPrivate ? (
              <div className={cn('flex items-center gap-2 text-slate-400', isHe && 'flex-row-reverse')}>
                <Lock className="w-3.5 h-3.5 shrink-0" />
                <p className="text-[11px]">{t.privateNoFeedback}</p>
              </div>
            ) : vote === null ? (
              <div className={cn('flex items-center gap-2', isHe && 'flex-row-reverse')}>
                <p className={cn('text-[11px] text-slate-500 dark:text-slate-400 flex-1', isHe && 'text-right')}>
                  {t.feedbackQuestion}
                </p>
                <div className="flex gap-1.5 shrink-0">
                  <button
                    onClick={() => handleVote('up')}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-md border border-slate-200 dark:border-slate-600 text-[11px] font-medium text-slate-600 dark:text-slate-300 hover:border-green-400 hover:bg-green-50 hover:text-green-700 dark:hover:bg-green-900/20 dark:hover:text-green-400 transition-all"
                    aria-label={t.voteUp}
                  >
                    <ThumbsUp className="w-3 h-3" />
                    {t.voteUp}
                  </button>
                  <button
                    onClick={() => handleVote('down')}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-md border border-slate-200 dark:border-slate-600 text-[11px] font-medium text-slate-600 dark:text-slate-300 hover:border-rose-400 hover:bg-rose-50 hover:text-rose-700 dark:hover:bg-rose-900/20 dark:hover:text-rose-400 transition-all"
                    aria-label={t.voteDown}
                  >
                    <ThumbsDown className="w-3 h-3" />
                    {t.voteDown}
                  </button>
                </div>
              </div>
            ) : (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className={cn('flex items-center gap-2', isHe && 'flex-row-reverse')}
              >
                <div className={cn(
                  'w-6 h-6 rounded-full flex items-center justify-center shrink-0',
                  vote === 'up' ? 'bg-green-100 dark:bg-green-900/30' : 'bg-rose-100 dark:bg-rose-900/30',
                )}>
                  {vote === 'up'
                    ? <ThumbsUp className="w-3 h-3 text-green-600 dark:text-green-400" />
                    : <ThumbsDown className="w-3 h-3 text-rose-600 dark:text-rose-400" />
                  }
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300">{t.feedbackThanks}</p>
              </motion.div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 pb-4 shrink-0">
          <button
            onClick={() => onOpenChange(false)}
            className="w-full py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            {t.closePanel}
          </button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
