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
  ExternalLink,
  Lightbulb,
  Quote,
  Copy,
  Check,
} from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';

type AnnotationSidePanelProps = {
  annotation: Annotation | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

const severityInfo = {
  outdated: {
    icon: '📅',
    title: 'Outdated Terminology',
    color: 'from-sky-500 to-sky-600',
    bgLight: 'bg-sky-50 dark:bg-sky-900/20',
    borderColor: 'border-sky-200 dark:border-sky-800',
  },
  biased: {
    icon: '⚖️',
    title: 'Biased Language',
    color: 'from-amber-500 to-amber-600',
    bgLight: 'bg-amber-50 dark:bg-amber-900/20',
    borderColor: 'border-amber-200 dark:border-amber-800',
  },
  potentially_offensive: {
    icon: '⚠️',
    title: 'Potentially Offensive',
    color: 'from-rose-500 to-rose-600',
    bgLight: 'bg-rose-50 dark:bg-rose-900/20',
    borderColor: 'border-rose-200 dark:border-rose-800',
  },
  factually_incorrect: {
    icon: '❌',
    title: 'Factually Incorrect',
    color: 'from-red-500 to-red-600',
    bgLight: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-red-200 dark:border-red-800',
  },
};

export default function AnnotationSidePanel({
  annotation,
  open,
  onOpenChange,
}: AnnotationSidePanelProps) {
  const [copied, setCopied] = useState(false);

  if (!annotation) return null;

  const info = severityInfo[annotation.severity] || severityInfo.biased;

  const handleCopySuggestion = async () => {
    if (annotation.suggestion) {
      await navigator.clipboard.writeText(annotation.suggestion);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-md p-0 overflow-hidden flex flex-col">
        {/* Header with gradient */}
        <div className={cn('relative overflow-hidden')}>
          {/* Background gradient */}
          <div className={cn('absolute inset-0 bg-gradient-to-br opacity-10', info.color)} />
          <div className="absolute inset-0 bg-gradient-to-b from-transparent to-white dark:to-slate-900" />

          <SheetHeader className="relative p-6 pb-4">
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="text-4xl mb-3"
            >
              {info.icon}
            </motion.div>
            <SheetTitle className="text-left">
              <motion.span
                initial={{ y: 10, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.1 }}
                className="text-xl font-bold text-slate-800 dark:text-white"
              >
                {info.title}
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
            {/* Original Term */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className={cn('p-4 rounded-xl border', info.bgLight, info.borderColor)}
            >
              <div className="flex items-center gap-2 mb-2">
                <Quote className="w-4 h-4 text-slate-400" />
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  Flagged Term
                </span>
              </div>
              <p className="text-lg font-semibold text-slate-800 dark:text-white">
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
                <div className="flex items-center gap-2 mb-3">
                  <Lightbulb className="w-5 h-5 text-pride-purple" />
                  <h3 className="font-semibold text-slate-800 dark:text-white">
                    Why is this problematic?
                  </h3>
                </div>
                <p className="text-slate-600 dark:text-slate-300 leading-relaxed">
                  {annotation.explanation}
                </p>
              </motion.div>
            )}

            {/* Suggestion */}
            {annotation.suggestion && (
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <ArrowRight className="w-5 h-5 text-pride-purple" />
                  <h3 className="font-semibold text-slate-800 dark:text-white">
                    Suggested Alternative
                  </h3>
                </div>
                <div className="relative group">
                  <div className="p-4 rounded-xl bg-gradient-to-r from-pride-purple/5 to-pride-pink/5 dark:from-pride-purple/10 dark:to-pride-pink/10 border border-pride-purple/20">
                    <p className="text-pride-purple font-medium text-lg pr-10">
                      {annotation.suggestion}
                    </p>
                  </div>
                  <button
                    onClick={handleCopySuggestion}
                    className="absolute top-3 right-3 p-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors shadow-sm"
                    title="Copy suggestion"
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
                    Copied to clipboard!
                  </motion.p>
                )}
              </motion.div>
            )}

            {/* References */}
            {annotation.references && annotation.references.length > 0 && (
              <motion.div
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.35 }}
              >
                <div className="flex items-center gap-2 mb-3">
                  <BookOpen className="w-5 h-5 text-pride-purple" />
                  <h3 className="font-semibold text-slate-800 dark:text-white">
                    Learn More
                  </h3>
                </div>
                <div className="space-y-2">
                  {annotation.references.map((ref, i) => (
                    <motion.a
                      key={i}
                      href={ref.url}
                      target="_blank"
                      rel="noreferrer"
                      initial={{ x: -10, opacity: 0 }}
                      animate={{ x: 0, opacity: 1 }}
                      transition={{ delay: 0.4 + i * 0.05 }}
                      className="flex items-center gap-3 p-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-pride-purple/50 hover:bg-pride-purple/5 transition-all group"
                    >
                      <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center group-hover:bg-pride-purple/10 transition-colors">
                        <ExternalLink className="w-5 h-5 text-slate-400 group-hover:text-pride-purple transition-colors" />
                      </div>
                      <div className="flex-1 min-w-0">
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
            Got it, close panel
          </button>
        </motion.div>
      </SheetContent>
    </Sheet>
  );
}
