'use client';

import { motion } from 'framer-motion';
import { useTranslations } from 'next-intl';
import {
  RotateCcw, FileText, BarChart3, Lock, Mail, Download,
  ChevronRight, Info,
} from 'lucide-react';
import type { Severity } from '@/components/SeverityBadge';
import { cn } from '@/lib/utils';

type ReportResult = {
  phrase: string;
  severity: Severity;
  category?: string;
  explanation: string;
  suggestion?: string;
  references?: Array<{ label: string; url: string }>;
};

interface MobileReportProps {
  fileName: string;
  privateMode: boolean;
  score: number;
  totalIssues: number;
  wordCount: number;
  results: ReportResult[];
  counts: Record<Severity, number>;
  recommendations: string[];
  hasAnyResults: boolean;
  onReset: () => void;
  onExport: () => void;
  onContact: () => void;
  onIssueClick: (result: ReportResult) => void;
}

const severityPriority: Severity[] = [
  'factually_incorrect', 'potentially_offensive', 'biased', 'outdated',
];

const severityBorderColor: Record<Severity, string> = {
  outdated: '#0ea5e9',
  biased: '#f59e0b',
  potentially_offensive: '#f97316',
  factually_incorrect: '#ef4444',
};

/**
 * Mobile-only, read-only summary report shown in place of the desktop
 * two-column interactive results view. Renders the same data the
 * downloadable PDF (lib/exportReport.ts) is built from — score, category
 * breakdown, findings, recommendations — as reflowing single-column HTML.
 * The heavy DocumentViewer / highlight tooltips are never mounted here.
 */
export default function MobileReport({
  fileName, privateMode, score, totalIssues, wordCount,
  results, counts, recommendations, hasAnyResults,
  onReset, onExport, onContact, onIssueClick,
}: MobileReportProps) {
  const t = useTranslations('analyzer');

  const categoryConfig: Record<Severity, { label: string; bar: string; dot: string; text: string }> = {
    outdated: { label: t('summaryCard.outdated'), bar: 'bg-sky-500', dot: 'bg-sky-400', text: 'text-sky-600 dark:text-sky-400' },
    biased: { label: t('summaryCard.biased'), bar: 'bg-amber-500', dot: 'bg-amber-400', text: 'text-amber-600 dark:text-amber-400' },
    potentially_offensive: { label: t('summaryCard.potentially_offensive'), bar: 'bg-orange-500', dot: 'bg-orange-400', text: 'text-orange-600 dark:text-orange-400' },
    factually_incorrect: { label: t('summaryCard.factually_incorrect'), bar: 'bg-red-500', dot: 'bg-red-400', text: 'text-red-600 dark:text-red-400' },
  };

  const llmCategoryConfig: Record<string, { label: string }> = {
    'Medicalization': { label: t('llmCategoryMedicalization') },
    'Generalization': { label: t('llmCategoryGeneralization') },
    'Demeaning Terminology': { label: t('llmCategoryDemeaning') },
  };

  return (
    <motion.div
      key="mobile-report"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-3 py-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <button onClick={onReset} className="btn-ghost p-2 rounded-lg flex-shrink-0" aria-label={t('analyzeAnother')}>
            <RotateCcw className="w-5 h-5" />
          </button>
          <div className="min-w-0">
            <h2 className="font-semibold text-sm text-slate-800 dark:text-white flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-pride-purple flex-shrink-0" />
              <span className="truncate">{fileName}</span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              {totalIssues} {totalIssues === 1 ? t('issueFound') : t('issuesFoundPlural')}
            </p>
          </div>
        </div>
        {privateMode && (
          <span className="flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-pride-purple/10 text-pride-purple flex-shrink-0">
            <Lock className="w-3 h-3" />
            {t('privateMode.badge')}
          </span>
        )}
      </div>

      {/* Desktop-feature note */}
      <div className="flex items-start gap-2 rounded-lg bg-pride-purple/5 border border-pride-purple/15 px-3 py-2.5 text-xs text-slate-600 dark:text-slate-300">
        <Info className="w-4 h-4 text-pride-purple flex-shrink-0 mt-0.5" />
        <span className="leading-relaxed">{t('mobileReportNote')}</span>
      </div>

      {/* Score card */}
      <div className="glass rounded-xl border shadow-sm px-4 py-4">
        <p className="text-[10px] uppercase text-slate-400 mb-2 font-semibold">{t('summaryCard.score')}</p>
        <div className="flex items-end justify-between gap-3">
          <div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-5xl font-black tabular-nums leading-none text-slate-900 dark:text-white">{score}</span>
              <span className="text-slate-400 text-lg">%</span>
            </div>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 px-3 py-2 text-center">
              <p className="text-xl font-black text-slate-900 dark:text-white tabular-nums leading-none">{totalIssues}</p>
              <p className="text-[9px] text-slate-400 mt-1 leading-none whitespace-nowrap">{t('summaryCard.totalIssues')}</p>
            </div>
            <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 px-3 py-2 text-center">
              <p className="text-xl font-black text-slate-900 dark:text-white tabular-nums leading-none">{wordCount.toLocaleString()}</p>
              <p className="text-[9px] text-slate-400 mt-1 leading-none whitespace-nowrap">{t('summaryCard.wordCount')}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Category breakdown */}
      {totalIssues > 0 && (
        <div className="glass rounded-xl border shadow-sm p-4">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-pride-purple" />
            <h3 className="text-sm font-semibold">{t('summaryCard.categories')}</h3>
          </div>
          {/* Plain counters — percentages over a handful of findings are noise. */}
          <div className="space-y-2">
            {severityPriority.map((sev) => {
              const cfg = categoryConfig[sev];
              const count = counts[sev];
              return (
                <div key={sev} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-1.5">
                    <span className={cn('w-2 h-2 rounded-full flex-shrink-0', cfg.dot)} />
                    <span className={cn('font-medium', cfg.text)}>{cfg.label}</span>
                  </span>
                  <span className="font-bold text-slate-600 dark:text-slate-300 tabular-nums">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Findings list */}
      <div className="flex flex-col gap-2" role="list" aria-label={t('a11y.issuesList')}>
        {!hasAnyResults ? (
          <div className="p-8 text-center glass rounded-xl border shadow-sm">
            <div className="text-4xl mb-3">🎉</div>
            <p className="text-green-600 dark:text-green-400 font-semibold text-sm">{t('noIssuesFound')}</p>
            <p className="text-xs text-slate-500 mt-1">{t('noIssuesMessage')}</p>
          </div>
        ) : (
          results.map((result, idx) => {
            const cfg = categoryConfig[result.severity];
            return (
              <button
                key={idx}
                onClick={() => onIssueClick(result)}
                className="w-full text-start rounded-lg border bg-white dark:bg-slate-900 shadow-sm border-l-[3px] transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pride-purple active:scale-[0.99]"
                style={{ borderLeftColor: severityBorderColor[result.severity] }}
                role="listitem"
              >
                <div className="px-3.5 py-3">
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-[10px] font-bold text-slate-300 dark:text-slate-600 flex-shrink-0 w-4 text-right tabular-nums">{idx + 1}</span>
                      <p className="font-semibold text-sm text-slate-800 dark:text-white leading-snug truncate">&ldquo;{result.phrase}&rdquo;</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-300 dark:text-slate-600 flex-shrink-0 rtl:rotate-180" />
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 mb-1.5 pl-6">
                    <span className={cn('flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border border-current', cfg.text)}>
                      <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', cfg.dot)} />
                      {cfg.label}
                    </span>
                    {result.category && llmCategoryConfig[result.category] && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400">
                        {llmCategoryConfig[result.category].label}
                      </span>
                    )}
                  </div>
                  {result.explanation && (
                    <p className="text-[12px] text-slate-500 dark:text-slate-400 leading-relaxed pl-6">{result.explanation}</p>
                  )}
                  {result.suggestion && (
                    <p className="text-[12px] mt-1.5 pl-6 leading-relaxed">
                      <span className="text-pride-purple font-medium italic">{t('suggestedFix')} </span>
                      <span className="text-slate-500 dark:text-slate-400 italic">{result.suggestion}</span>
                    </p>
                  )}
                </div>
              </button>
            );
          })
        )}
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="glass rounded-xl border shadow-sm p-4">
          <h3 className="text-sm font-semibold mb-2.5">{t('summaryCard.recommendations')}</h3>
          <ul className="space-y-2">
            {recommendations.map((rec, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                <span className="w-1.5 h-1.5 rounded-full bg-pride-purple flex-shrink-0 mt-1.5" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col gap-2 pt-1 pb-4">
        <button
          onClick={onExport}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-pride-purple text-white text-sm font-semibold shadow-sm active:scale-[0.99] transition-transform"
        >
          <Download className="w-4 h-4" />
          {t('downloadReport')}
        </button>
        <div className="flex gap-2">
          <button onClick={onContact} className="btn-ghost flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium">
            <Mail className="w-4 h-4" />
            {t('contactUs')}
          </button>
          <button onClick={onReset} className="btn-ghost flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-sm font-medium">
            <RotateCcw className="w-4 h-4" />
            {t('analyzeAnother')}
          </button>
        </div>
      </div>
    </motion.div>
  );
}
