'use client';

import { motion } from 'framer-motion';
import React, { useState, useEffect, useMemo } from 'react';
import { ArrowRight, Check } from 'lucide-react';

interface DemoPreviewProps {
  isHebrew: boolean;
  translations: {
    title: string;
    subtitle: string;
    label: string;
    issuesDetected: string;
    demoText: string;
    term1: string;
    suggestion1: string;
    term2: string;
    suggestion2: string;
    outdated: string;
    biased: string;
  };
}

const severityColors = {
  outdated: 'bg-sky-200/80 dark:bg-sky-900/60 border-b-2 border-sky-500',
  biased: 'bg-amber-200/80 dark:bg-amber-900/60 border-b-2 border-amber-500',
  potentially_offensive: 'bg-rose-200/80 dark:bg-rose-900/60 border-b-2 border-rose-500',
  factually_incorrect: 'bg-red-200/80 dark:bg-red-900/60 border-b-2 border-red-500',
};

const DemoPreview = React.memo(function DemoPreview({ isHebrew, translations }: DemoPreviewProps) {
  const [activeHighlight, setActiveHighlight] = useState<number | null>(null);

  // Build highlights based on translations
  const highlights = useMemo(() => {
    const text = translations.demoText;
    const term1Start = text.indexOf(translations.term1);
    const term2Start = text.indexOf(translations.term2);

    return [
      {
        term: translations.term1,
        start: term1Start,
        end: term1Start + translations.term1.length,
        severity: 'outdated',
        suggestion: translations.suggestion1,
        severityLabel: translations.outdated,
      },
      {
        term: translations.term2,
        start: term2Start,
        end: term2Start + translations.term2.length,
        severity: 'biased',
        suggestion: translations.suggestion2,
        severityLabel: translations.biased,
      },
    ].filter(h => h.start >= 0); // Only include highlights that are found in text
  }, [translations]);

  useEffect(() => {
    // Animate through highlights
    const interval = setInterval(() => {
      setActiveHighlight((prev) => {
        return prev === null ? 0 : prev === highlights.length - 1 ? null : prev + 1;
      });
    }, 2500);

    return () => clearInterval(interval);
  }, [highlights.length]);

  const renderHighlightedText = () => {
    const demoText = translations.demoText;
    const parts: React.ReactNode[] = [];
    let cursor = 0;

    const sortedHighlights = [...highlights].sort((a, b) => a.start - b.start);

    sortedHighlights.forEach((h, idx) => {
      if (h.start > cursor) {
        parts.push(
          <span key={`text-${idx}`} className="text-slate-600 dark:text-slate-300">
            {demoText.slice(cursor, h.start)}
          </span>
        );
      }

      const isActive = activeHighlight === idx;
      parts.push(
        <motion.span
          key={`highlight-${idx}`}
          className={`relative rounded-sm px-0.5 cursor-pointer transition-all duration-300 ${
            severityColors[h.severity as keyof typeof severityColors]
          } ${isActive ? 'ring-2 ring-pride-purple/50 scale-105' : ''}`}
          animate={isActive ? { scale: [1, 1.02, 1] } : {}}
          transition={{ duration: 0.5 }}
        >
          {h.term}
          {isActive && (
            <motion.div
              initial={{ opacity: 0, y: 5, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className={`absolute ${isHebrew ? 'right-0' : 'left-0'} top-full mt-3 z-10 w-72 p-4 rounded-xl bg-white dark:bg-slate-800 shadow-2xl border border-slate-200 dark:border-slate-700`}
            >
              <div className="flex items-center gap-2 mb-3">
                <span
                  className={`w-2.5 h-2.5 rounded-full ${
                    h.severity === 'outdated' ? 'bg-sky-500' : 'bg-amber-500'
                  }`}
                />
                <span className="text-sm font-semibold uppercase text-slate-500">
                  {h.severityLabel}
                </span>
              </div>
              <div className="flex items-start gap-2">
                <ArrowRight className={`w-5 h-5 text-pride-purple flex-shrink-0 mt-0.5 ${isHebrew ? 'rotate-180' : ''}`} />
                <span className="text-base text-pride-purple font-medium">{h.suggestion}</span>
              </div>
            </motion.div>
          )}
        </motion.span>
      );
      cursor = h.end;
    });

    if (cursor < demoText.length) {
      parts.push(
        <span key="text-end" className="text-slate-600 dark:text-slate-300">
          {demoText.slice(cursor)}
        </span>
      );
    }

    return parts;
  };

  return (
    <section className="py-12 px-4">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-8"
        >
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-800 dark:text-white mb-3">
            {translations.title}
          </h2>
          <p className="text-slate-600 dark:text-slate-400">
            {translations.subtitle}
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="relative"
        >
          {/* Browser Chrome */}
          <div className="rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 shadow-2xl bg-white dark:bg-slate-900">
            {/* Browser Header */}
            <div className="flex items-center gap-2 px-4 py-3 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-400" />
                <div className="w-3 h-3 rounded-full bg-yellow-400" />
                <div className="w-3 h-3 rounded-full bg-green-400" />
              </div>
              <div className="flex-1 flex justify-center">
                <div className="px-4 py-1 rounded-md bg-white dark:bg-slate-700 text-xs text-slate-500 dark:text-slate-400 font-mono">
                  inclusify.app/analyze
                </div>
              </div>
            </div>

            {/* Content */}
            <div className="p-8 sm:p-10">
              <div className={`flex items-center gap-3 mb-6 ${isHebrew ? 'flex-row-reverse' : ''}`}>
                <div className="px-4 py-1.5 rounded-full bg-pride-purple/10 text-pride-purple text-sm font-semibold">
                  {translations.label}
                </div>
                <div className={`flex items-center gap-1.5 text-sm text-slate-500 ${isHebrew ? 'flex-row-reverse' : ''}`}>
                  <Check className="w-4 h-4 text-green-500" />
                  <span>2 {translations.issuesDetected}</span>
                </div>
              </div>

              <div className={`text-lg sm:text-xl leading-relaxed relative min-h-[120px] ${isHebrew ? 'text-right' : ''}`} dir={isHebrew ? 'rtl' : 'ltr'}>
                {renderHighlightedText()}
              </div>
            </div>
          </div>

          {/* Decorative Elements */}
          <div className="absolute -z-10 inset-0 blur-3xl opacity-20">
            <div className="absolute top-0 right-0 w-32 h-32 bg-pride-purple rounded-full" />
            <div className="absolute bottom-0 left-0 w-32 h-32 bg-pride-pink rounded-full" />
          </div>
        </motion.div>
      </div>
    </section>
  );
});

export default DemoPreview;
