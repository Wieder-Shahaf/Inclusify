'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Severity } from './SeverityBadge';
import {
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Lightbulb,
  BarChart3,
  FileText,
  Download
} from 'lucide-react';

interface Translations {
  score: string;
  totalIssues: string;
  wordCount: string;
  categories: string;
  recommendations: string;
  excellent: string;
  good: string;
  needsImprovement: string;
  requiresAttention: string;
  outdated: string;
  biased: string;
  offensive: string;
  incorrect: string;
  exportReport: string;
}

interface AnalysisSummaryProps {
  counts: Record<Severity, number>;
  score: number;
  recommendations: string[];
  wordCount: number;
  onExport?: () => void;
  translations?: Translations;
}

const defaultTranslations: Translations = {
  score: 'Inclusivity Score',
  totalIssues: 'Total Issues',
  wordCount: 'Word Count',
  categories: 'Issues by Category',
  recommendations: 'Recommendations',
  excellent: 'Excellent',
  good: 'Good',
  needsImprovement: 'Needs Improvement',
  requiresAttention: 'Requires Attention',
  outdated: 'Outdated',
  biased: 'Biased',
  offensive: 'Offensive',
  incorrect: 'Incorrect',
  exportReport: 'Export Report',
};

function getScoreColor(score: number): string {
  if (score >= 90) return 'text-green-500';
  if (score >= 70) return 'text-amber-500';
  if (score >= 50) return 'text-orange-500';
  return 'text-red-500';
}

function getScoreGradient(score: number): string {
  if (score >= 90) return 'from-green-500 to-emerald-400';
  if (score >= 70) return 'from-amber-500 to-yellow-400';
  if (score >= 50) return 'from-orange-500 to-amber-400';
  return 'from-red-500 to-rose-400';
}

function getScoreLabel(score: number, translations: Translations): string {
  if (score >= 90) return translations.excellent;
  if (score >= 70) return translations.good;
  if (score >= 50) return translations.needsImprovement;
  return translations.requiresAttention;
}

export default function AnalysisSummary({
  counts,
  score,
  recommendations,
  wordCount,
  onExport,
  translations,
}: AnalysisSummaryProps) {
  const t = { ...defaultTranslations, ...translations };

  const categoryConfig = {
    outdated: {
      label: t.outdated,
      color: 'bg-sky-500',
      lightColor: 'bg-sky-100 dark:bg-sky-900/30',
      textColor: 'text-sky-600 dark:text-sky-400',
    },
    biased: {
      label: t.biased,
      color: 'bg-amber-500',
      lightColor: 'bg-amber-100 dark:bg-amber-900/30',
      textColor: 'text-amber-600 dark:text-amber-400',
    },
    offensive: {
      label: t.offensive,
      color: 'bg-rose-500',
      lightColor: 'bg-rose-100 dark:bg-rose-900/30',
      textColor: 'text-rose-600 dark:text-rose-400',
    },
    incorrect: {
      label: t.incorrect,
      color: 'bg-red-500',
      lightColor: 'bg-red-100 dark:bg-red-900/30',
      textColor: 'text-red-600 dark:text-red-400',
    },
  };

  const totalIssues = counts.outdated + counts.biased + counts.offensive + counts.incorrect;
  const maxCount = Math.max(...Object.values(counts), 1);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-4"
    >
      {/* Inclusivity Score Card */}
      <div className="p-5 rounded-xl glass border overflow-hidden relative">
        {/* Background Decoration */}
        <div className="absolute top-0 right-0 w-32 h-32 opacity-10">
          <div className={cn(
            'absolute inset-0 rounded-full blur-2xl',
            `bg-gradient-to-br ${getScoreGradient(score)}`
          )} />
        </div>

        <div className="relative flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-500 dark:text-slate-400 mb-1">
              {t.score}
            </p>
            <div className="flex items-baseline gap-2">
              <motion.span
                className={cn('text-4xl font-bold', getScoreColor(score))}
                initial={{ scale: 0.5 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 200, damping: 15 }}
              >
                {score}
              </motion.span>
              <span className="text-slate-400">/100</span>
            </div>
            <p className={cn('text-sm font-medium mt-1', getScoreColor(score))}>
              {getScoreLabel(score, t)}
            </p>
          </div>

          {/* Circular Progress */}
          <div className="relative w-20 h-20">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="40"
                cy="40"
                r="36"
                stroke="currentColor"
                strokeWidth="6"
                fill="none"
                className="text-slate-100 dark:text-slate-800"
              />
              <motion.circle
                cx="40"
                cy="40"
                r="36"
                stroke="url(#scoreGradient)"
                strokeWidth="6"
                fill="none"
                strokeLinecap="round"
                initial={{ strokeDasharray: '0 226' }}
                animate={{ strokeDasharray: `${(score / 100) * 226} 226` }}
                transition={{ duration: 1, ease: 'easeOut' }}
              />
              <defs>
                <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor={score >= 70 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444'} />
                  <stop offset="100%" stopColor={score >= 70 ? '#10b981' : score >= 50 ? '#eab308' : '#f43f5e'} />
                </linearGradient>
              </defs>
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              {score >= 70 ? (
                <CheckCircle2 className="w-6 h-6 text-green-500" />
              ) : (
                <AlertCircle className={cn('w-6 h-6', getScoreColor(score))} />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <AlertCircle className="w-4 h-4" />
            <span className="text-xs">{t.totalIssues}</span>
          </div>
          <p className="text-2xl font-bold text-slate-800 dark:text-white">
            {totalIssues}
          </p>
        </div>
        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <FileText className="w-4 h-4" />
            <span className="text-xs">{t.wordCount}</span>
          </div>
          <p className="text-2xl font-bold text-slate-800 dark:text-white">
            {wordCount.toLocaleString()}
          </p>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="p-4 rounded-xl glass border">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-4 h-4 text-pride-purple" />
          <h3 className="text-sm font-semibold">{t.categories}</h3>
        </div>
        <div className="space-y-3">
          {(Object.keys(categoryConfig) as Severity[]).map((severity) => {
            const config = categoryConfig[severity];
            const count = counts[severity];
            const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;

            return (
              <div key={severity}>
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className={cn('font-medium', config.textColor)}>
                    {config.label}
                  </span>
                  <span className="text-slate-600 dark:text-slate-300 font-semibold">
                    {count}
                  </span>
                </div>
                <div className="h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                  <motion.div
                    className={cn('h-full rounded-full', config.color)}
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="p-4 rounded-xl glass border">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="w-4 h-4 text-pride-purple" />
            <h3 className="text-sm font-semibold">{t.recommendations}</h3>
          </div>
          <ul className="space-y-2">
            {recommendations.map((rec, index) => (
              <motion.li
                key={index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300"
              >
                <TrendingUp className="w-4 h-4 text-pride-purple flex-shrink-0 mt-0.5" />
                <span>{rec}</span>
              </motion.li>
            ))}
          </ul>
        </div>
      )}

      {/* Export Button */}
      {onExport && (
        <motion.button
          onClick={onExport}
          className="w-full py-3 px-4 rounded-xl border-2 border-dashed border-slate-200 dark:border-slate-700 hover:border-pride-purple/50 hover:bg-pride-purple/5 transition-all flex items-center justify-center gap-2 text-slate-600 dark:text-slate-400"
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
        >
          <Download className="w-4 h-4" />
          <span className="font-medium">{t.exportReport}</span>
        </motion.button>
      )}
    </motion.div>
  );
}
