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
  ArrowRight,
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
    icon: '📅',
    title: { en: 'Outdated Terminology', he: 'מינוח מיושן' },
    color: 'from-sky-500 to-sky-600',
    bgLight: 'bg-sky-50 dark:bg-sky-900/20',
    borderColor: 'border-sky-200 dark:border-sky-800',
  },
  biased: {
    icon: '⚖️',
    title: { en: 'Biased Language', he: 'שפה מוטה' },
    color: 'from-amber-500 to-amber-600',
    bgLight: 'bg-amber-50 dark:bg-amber-900/20',
    borderColor: 'border-amber-200 dark:border-amber-800',
  },
  potentially_offensive: {
    icon: '⚠️',
    title: { en: 'Potentially Offensive', he: 'עלול לפגוע' },
    color: 'from-rose-500 to-rose-600',
    bgLight: 'bg-rose-50 dark:bg-rose-900/20',
    borderColor: 'border-rose-200 dark:border-rose-800',
  },
  factually_incorrect: {
    icon: '❌',
    title: { en: 'Factually Incorrect', he: 'שגוי עובדתית' },
    color: 'from-red-500 to-red-600',
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

  // RTL when locale is Hebrew OR when the flagged text/explanation contains Hebrew characters
  const hasHebrew = (s?: string) => !!s && /[֐-׿]/.test(s);
  const isHe =
    locale === 'he' ||
    hasHebrew(annotation?.label) ||
    hasHebrew(annotation?.explanation);

  // Reset feedback state whenever a new annotation is shown
  useEffect(() => {
    setVote(null);
  }, [annotation?.start, annotation?.end]);

  if (!annotation) return null;

  const info = severityInfo[annotation.severity] || severityInfo.biased;

  const t = {
    flaggedTerm:         isHe ? 'מונח מסומן'                : 'Flagged Term',
    whyProblematic:      isHe ? 'מדוע זה בעייתי?'           : 'Why is this problematic?',
    modelConfidence:     isHe ? 'ביטחון המודל'               : 'Model confidence',
    suggestedAlt:        isHe ? 'חלופה מומלצת'               : 'Suggested Alternative',
    copySuggestion:      isHe ? 'העתק הצעה'                  : 'Copy suggestion',
    copied:              isHe ? '!הועתק ללוח'                : 'Copied to clipboard!',
    inclusiveVersion:    isHe ? 'גרסה מכלילה'                : 'Inclusive version',
    learnMore:           isHe ? 'למידע נוסף'                  : 'Learn More',
    closePanel:          isHe ? 'הבנתי, סגור'                : 'Got it, close panel',
    feedbackQuestion:    isHe ? 'האם הדגל הזה מועיל?'       : 'Was this flag helpful?',
    voteUp:              isHe ? 'כן, מועיל'                  : 'Yes, helpful',
    voteDown:            isHe ? 'לא, זיהוי שגוי'             : 'No, false detection',
    feedbackThanks:      isHe ? 'תודה על המשוב!'             : 'Thanks for your feedback!',
    privateNoFeedback:   isHe ? 'משוב אינו זמין במצב פרטי'  : 'Feedback unavailable in private mode',
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
        className="w-full sm:max-w-md p-0 overflow-hidden flex flex-col"
        dir={isHe ? 'rtl' : 'ltr'}
      >
        {/* Header with gradient */}
        <div className={cn('relative overflow-hidden')}>
          <div className={cn('absolute inset-0 bg-gradient-to-br opacity-10', info.color)} />
          <div className="absolute inset-0 bg-gradient-to-b from-transparent to-white dark:to-slate-900" />

          <SheetHeader className={cn('relative p-6 pb-4', isHe ? 'text-right' : 'text-left')}>
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="text-4xl mb-3"
            >
              {info.icon}
            </motion.div>
            <SheetTitle className={isHe ? 'text-right' : 'text-left'}>
              <motion.span
                initial={{ y: 10, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.1 }}
                className="text-xl font-bold text-slate-800 dark:text-white"
              >
                {info.title[isHe ? 'he' : 'en']}
              </motion.span>
            </SheetTitle>
            <motion.div
              initial={{ y: 10, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.15 }}
              className="mt-2"
            >
              <SeverityBadge level={annotation.severity} />
            </motion.div>
          </SheetHeader>
        </div>

        {/* Content - Scrollable */}
        <div className="flex-1 overflow-y-auto px-6 pb-6">
          <div className="space-y-6">
            {/* Flagged Term */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className={cn('p-4 rounded-xl border', info.bgLight, info.borderColor)}
            >
              <div className={cn('flex items-center gap-2 mb-2', isHe && 'flex-row-reverse')}>
                <Quote className="w-4 h-4 text-slate-400" />
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  {t.flaggedTerm}
                </span>
              </div>
              <p className={cn('text-lg font-semibold text-slate-800 dark:text-white', isHe && 'text-right')}>
                &ldquo;{annotation.label}&rdquo;
              </p>
            </motion.div>

            {/* Explanation */}
            {annotation.explanation && (
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.25 }}
              >
                <div className={cn('flex items-center gap-2 mb-3', isHe && 'flex-row-reverse')}>
                  <Lightbulb className="w-5 h-5 text-pride-purple" />
                  <h3 className="font-semibold text-slate-800 dark:text-white">
                    {t.whyProblematic}
                  </h3>
                </div>
                <p className={cn('text-slate-600 dark:text-slate-300 leading-relaxed', isHe && 'text-right')}>
                  {annotation.explanation}
                </p>
              </motion.div>
            )}

            {/* Confidence */}
            {annotation.confidence != null && (
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.28 }}
              >
                <div className={cn('flex items-center gap-2 mb-2', isHe && 'flex-row-reverse')}>
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    {t.modelConfidence}
                  </span>
                  <span className="text-sm font-semibold text-slate-800 dark:text-white">
                    {Math.round(annotation.confidence * 100)}%
                  </span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full bg-pride-purple"
                    style={{ width: `${annotation.confidence * 100}%` }}
                  />
                </div>
              </motion.div>
            )}

            {/* Suggestion */}
            {annotation.suggestion && (
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                <div className={cn('flex items-center gap-2 mb-3', isHe && 'flex-row-reverse')}>
                  <ArrowRight className={cn('w-5 h-5 text-pride-purple', isHe && 'rotate-180')} />
                  <h3 className="font-semibold text-slate-800 dark:text-white">
                    {t.suggestedAlt}
                  </h3>
                </div>
                <div className="relative group">
                  <div className="p-4 rounded-xl bg-gradient-to-r from-pride-purple/5 to-pride-pink/5 dark:from-pride-purple/10 dark:to-pride-pink/10 border border-pride-purple/20">
                    <p className={cn('text-pride-purple font-medium text-lg', isHe ? 'pl-10 text-right' : 'pr-10')}>
                      {annotation.suggestion}
                    </p>
                  </div>
                  <button
                    onClick={handleCopySuggestion}
                    className={cn(
                      'absolute top-3 p-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm',
                      isHe ? 'left-3' : 'right-3'
                    )}
                    title={t.copySuggestion}
                  >
                    {copied ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4 text-slate-400" />
                    )}
                  </button>
                </div>
                {copied && (
                  <motion.p
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-xs text-green-500 mt-2 text-center"
                  >
                    {t.copied}
                  </motion.p>
                )}
              </motion.div>
            )}

            {/* Inclusive Sentence */}
            {annotation.inclusive_sentence && (
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.33 }}
              >
                <div className={cn('flex items-center gap-2 mb-3', isHe && 'flex-row-reverse')}>
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                  <h3 className="font-semibold text-slate-800 dark:text-white">
                    {t.inclusiveVersion}
                  </h3>
                </div>
                <div className="p-4 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                  <p className={cn('text-green-800 dark:text-green-200 leading-relaxed', isHe && 'text-right')}>
                    {annotation.inclusive_sentence}
                  </p>
                </div>
              </motion.div>
            )}

            {/* References */}
            {annotation.references && annotation.references.length > 0 && (
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.35 }}
              >
                <div className={cn('flex items-center gap-2 mb-3', isHe && 'flex-row-reverse')}>
                  <BookOpen className="w-5 h-5 text-pride-purple" />
                  <h3 className="font-semibold text-slate-800 dark:text-white">
                    {t.learnMore}
                  </h3>
                </div>
                <div className="space-y-2">
                  {annotation.references.map((ref, i) => (
                    <motion.a
                      key={i}
                      href={ref.url}
                      target="_blank"
                      rel="noreferrer"
                      initial={{ x: isHe ? 10 : -10, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      transition={{ delay: 0.4 + i * 0.05 }}
                      className={cn(
                        'flex items-center gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-pride-purple/50 hover:bg-pride-purple/5 transition-all group',
                        isHe && 'flex-row-reverse'
                      )}
                    >
                      <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center group-hover:bg-pride-purple/10 transition-colors shrink-0">
                        <ExternalLink className="w-5 h-5 text-slate-400 group-hover:text-pride-purple transition-colors" />
                      </div>
                      <div className={cn('flex-1 min-w-0', isHe && 'text-right')}>
                        <p className="font-medium text-slate-800 dark:text-white group-hover:text-pride-purple transition-colors truncate">
                          {ref.label}
                        </p>
                        <p className="text-xs text-slate-400 truncate">
                          {new URL(ref.url).hostname}
                        </p>
                      </div>
                    </motion.a>
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        </div>

        {/* Feedback — thumbs up/down (hidden in private mode) */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.42 }}
          className="px-6 pb-4"
        >
          <div className={cn(
            'rounded-xl border border-slate-200 dark:border-slate-700 p-4',
            'bg-slate-50 dark:bg-slate-800/50',
          )}>
            {isPrivate ? (
              <div className={cn('flex items-center gap-2 text-slate-400 dark:text-slate-500', isHe && 'flex-row-reverse')}>
                <Lock className="w-4 h-4 shrink-0" />
                <p className="text-xs">{t.privateNoFeedback}</p>
              </div>
            ) : vote === null ? (
              <>
                <p className={cn(
                  'text-xs font-medium text-slate-500 dark:text-slate-400 mb-3',
                  isHe ? 'text-right' : 'text-left',
                )}>
                  {t.feedbackQuestion}
                </p>
                <div className={cn('flex gap-2', isHe && 'flex-row-reverse')}>
                  <button
                    onClick={() => handleVote('up')}
                    className={cn(
                      'flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg border text-sm font-medium transition-all',
                      'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300',
                      'hover:border-green-400 hover:bg-green-50 hover:text-green-700',
                      'dark:hover:border-green-500 dark:hover:bg-green-900/20 dark:hover:text-green-400',
                    )}
                    aria-label={t.voteUp}
                  >
                    <ThumbsUp className="w-4 h-4" />
                    {t.voteUp}
                  </button>
                  <button
                    onClick={() => handleVote('down')}
                    className={cn(
                      'flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg border text-sm font-medium transition-all',
                      'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300',
                      'hover:border-rose-400 hover:bg-rose-50 hover:text-rose-700',
                      'dark:hover:border-rose-500 dark:hover:bg-rose-900/20 dark:hover:text-rose-400',
                    )}
                    aria-label={t.voteDown}
                  >
                    <ThumbsDown className="w-4 h-4" />
                    {t.voteDown}
                  </button>
                </div>
              </>
            ) : (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className={cn('flex items-center gap-2', isHe ? 'flex-row-reverse' : '')}
              >
                <div className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
                  vote === 'up'
                    ? 'bg-green-100 dark:bg-green-900/30'
                    : 'bg-rose-100 dark:bg-rose-900/30',
                )}>
                  {vote === 'up'
                    ? <ThumbsUp className="w-4 h-4 text-green-600 dark:text-green-400" />
                    : <ThumbsDown className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                  }
                </div>
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  {t.feedbackThanks}
                </p>
              </motion.div>
            )}
          </div>
        </motion.div>

        {/* Footer */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="p-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50"
        >
          <button
            onClick={() => onOpenChange(false)}
            className="w-full btn-primary py-3"
          >
            {t.closePanel}
          </button>
        </motion.div>
      </SheetContent>
    </Sheet>
  );
}
