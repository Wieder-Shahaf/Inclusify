'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/contexts/AuthContext';
import { getHistory, type HistoryItem } from '@/lib/api/client';
import {
  History,
  FileText,
  LogIn,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  AlertCircle,
  Clock,
  BarChart2,
} from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

const PAGE_SIZE = 15;

// Score badge color
function scoreColor(score: number | null): string {
  if (score === null) return 'text-slate-400';
  if (score >= 80) return 'text-emerald-600 dark:text-emerald-400';
  if (score >= 60) return 'text-yellow-600 dark:text-yellow-400';
  return 'text-red-600 dark:text-red-400';
}

function scoreBg(score: number | null): string {
  if (score === null) return 'bg-slate-100 dark:bg-slate-800';
  if (score >= 80) return 'bg-emerald-50 dark:bg-emerald-900/30';
  if (score >= 60) return 'bg-yellow-50 dark:bg-yellow-900/30';
  return 'bg-red-50 dark:bg-red-900/30';
}

function formatDate(iso: string, locale: string): string {
  return new Date(iso).toLocaleDateString(locale === 'he' ? 'he-IL' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// Severity dot strip
function SeverityDots({ high, medium, low }: { high: number; medium: number; low: number }) {
  return (
    <div className="flex items-center gap-1.5 text-xs">
      {high > 0 && (
        <span className="flex items-center gap-0.5 text-red-600 dark:text-red-400 font-medium">
          <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
          {high}
        </span>
      )}
      {medium > 0 && (
        <span className="flex items-center gap-0.5 text-amber-600 dark:text-amber-400 font-medium">
          <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
          {medium}
        </span>
      )}
      {low > 0 && (
        <span className="flex items-center gap-0.5 text-sky-600 dark:text-sky-400 font-medium">
          <span className="w-2 h-2 rounded-full bg-sky-400 inline-block" />
          {low}
        </span>
      )}
      {high === 0 && medium === 0 && low === 0 && (
        <span className="text-emerald-600 dark:text-emerald-400 font-medium">✓</span>
      )}
    </div>
  );
}

function ModeChip({ mode, t }: { mode: string | null; t: ReturnType<typeof useTranslations> }) {
  const label = mode ? (t(`modes.${mode}`) as string) : '—';
  const cls =
    mode === 'llm'
      ? 'bg-violet-100 dark:bg-violet-900/40 text-violet-700 dark:text-violet-300'
      : mode === 'hybrid'
        ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
        : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400';
  return (
    <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', cls)}>{label}</span>
  );
}

// Skeleton loader row
function SkeletonRow() {
  return (
    <tr className="animate-pulse border-b border-slate-100 dark:border-slate-800">
      {Array.from({ length: 6 }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-full" />
        </td>
      ))}
    </tr>
  );
}

export default function HistoryPage() {
  const params = useParams();
  const locale = (params?.locale as string) || 'en';
  const router = useRouter();
  const t = useTranslations('history');
  const { user, isLoading: authLoading } = useAuth();

  const [items, setItems] = useState<HistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [noDb, setNoDb] = useState(false);

  const fetchPage = useCallback(async (pageIndex: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getHistory(PAGE_SIZE, pageIndex * PAGE_SIZE);
      setItems(data.items);
      setTotal(data.total);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      if (msg.includes('503') || msg.toLowerCase().includes('database')) {
        setNoDb(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && user) {
      fetchPage(page);
    }
  }, [authLoading, user, page, fetchPage]);

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const from = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const to = Math.min((page + 1) * PAGE_SIZE, total);

  // ── Auth loading ──────────────────────────────────────────────────────────
  if (authLoading) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <div className="w-8 h-8 rounded-full border-2 border-pride-purple border-t-transparent animate-spin" />
      </div>
    );
  }

  // ── Not logged in ─────────────────────────────────────────────────────────
  if (!user) {
    return (
      <div className="flex-1 flex items-center justify-center py-16">
        <div className="text-center max-w-sm mx-auto px-4">
          <div className="mb-6 flex justify-center">
            <div className="p-4 bg-slate-100 dark:bg-slate-800 rounded-full">
              <History className="w-12 h-12 text-slate-400" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-3">
            {t('title')}
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mb-6">{t('loginRequired')}</p>
          <Link
            href={`/${locale}/login`}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-pride-purple text-white rounded-lg font-medium hover:bg-pride-purple/90 transition-colors"
          >
            <LogIn className="w-4 h-4" />
            {t('loginCta')}
          </Link>
        </div>
      </div>
    );
  }

  // ── No DB ─────────────────────────────────────────────────────────────────
  if (noDb) {
    return (
      <div className="flex-1 flex items-center justify-center py-16">
        <div className="text-center max-w-sm mx-auto px-4">
          <AlertCircle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
          <p className="text-slate-700 dark:text-slate-300">{t('noDb')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col py-8 gap-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <History className="w-6 h-6 text-pride-purple" />
            {t('title')}
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{t('subtitle')}</p>
        </div>
        <button
          onClick={() => fetchPage(page)}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors disabled:opacity-40"
        >
          <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{t('errorLoading')}</span>
          <button
            onClick={() => fetchPage(page)}
            className="ml-auto underline hover:no-underline"
          >
            {t('retry')}
          </button>
        </div>
      )}

      {/* Table card */}
      <div className="glass rounded-xl border border-white/20 dark:border-slate-700/50 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50/80 dark:bg-slate-800/50">
                <th className="px-4 py-3 text-start font-semibold text-slate-600 dark:text-slate-400 whitespace-nowrap">
                  {t('date')}
                </th>
                <th className="px-4 py-3 text-start font-semibold text-slate-600 dark:text-slate-400">
                  {t('document')}
                </th>
                <th className="px-4 py-3 text-center font-semibold text-slate-600 dark:text-slate-400">
                  {t('score')}
                </th>
                <th className="px-4 py-3 text-start font-semibold text-slate-600 dark:text-slate-400">
                  {t('issues')}
                </th>
                <th className="px-4 py-3 text-center font-semibold text-slate-600 dark:text-slate-400">
                  {t('language')}
                </th>
                <th className="px-4 py-3 text-center font-semibold text-slate-600 dark:text-slate-400">
                  {t('mode')}
                </th>
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} />)
                : items.length === 0
                  ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-16 text-center">
                        <div className="flex flex-col items-center gap-3">
                          <BarChart2 className="w-10 h-10 text-slate-300 dark:text-slate-600" />
                          <p className="font-medium text-slate-500 dark:text-slate-400">
                            {t('empty')}
                          </p>
                          <p className="text-xs text-slate-400 dark:text-slate-500 max-w-xs text-center">
                            {t('emptyDesc')}
                          </p>
                          <Link
                            href={`/${locale}/analyze`}
                            className="mt-2 inline-flex items-center gap-1.5 px-4 py-2 bg-pride-purple text-white rounded-lg text-sm font-medium hover:bg-pride-purple/90 transition-colors"
                          >
                            <FileText className="w-4 h-4" />
                            {t('analyzeNow')}
                          </Link>
                        </div>
                      </td>
                    </tr>
                  )
                  : items.map((item) => (
                    <tr
                      key={item.run_id}
                      className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      {/* Date */}
                      <td className="px-4 py-3 whitespace-nowrap text-slate-500 dark:text-slate-400">
                        <div className="flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 shrink-0" />
                          {formatDate(item.created_at, locale)}
                        </div>
                      </td>

                      {/* Document name */}
                      <td className="px-4 py-3 max-w-[220px]">
                        <div className="flex items-center gap-2 min-w-0">
                          <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                          <span
                            className="truncate text-slate-800 dark:text-slate-200 font-medium"
                            title={item.original_filename ?? undefined}
                          >
                            {item.original_filename || t('pastedText')}
                          </span>
                        </div>
                        {item.word_count != null && (
                          <p className="mt-0.5 text-xs text-slate-400 ps-6">
                            {item.word_count.toLocaleString()} words
                          </p>
                        )}
                      </td>

                      {/* Score */}
                      <td className="px-4 py-3 text-center">
                        {item.score != null ? (
                          <span
                            className={cn(
                              'inline-block px-2.5 py-0.5 rounded-full text-sm font-bold',
                              scoreBg(item.score),
                              scoreColor(item.score),
                            )}
                          >
                            {item.score}
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      {/* Issues breakdown */}
                      <td className="px-4 py-3">
                        <SeverityDots
                          high={item.high_count}
                          medium={item.medium_count}
                          low={item.low_count}
                        />
                        {item.total_findings > 0 && (
                          <p className="mt-0.5 text-xs text-slate-400">
                            {item.total_findings} total
                          </p>
                        )}
                      </td>

                      {/* Language */}
                      <td className="px-4 py-3 text-center">
                        <span className="uppercase text-xs font-semibold text-slate-500 dark:text-slate-400 tracking-wide">
                          {item.language === 'auto' ? '—' : item.language.toUpperCase()}
                        </span>
                      </td>

                      {/* Mode */}
                      <td className="px-4 py-3 text-center">
                        <ModeChip mode={item.analysis_mode} t={t} />
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between text-sm text-slate-600 dark:text-slate-400">
          <span>
            {t('showingOf', { from, to, total })}
          </span>
          <div className="flex items-center gap-2">
            <button
              disabled={page === 0 || loading}
              onClick={() => { setPage(p => p - 1); router.refresh(); }}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              {t('previous')}
            </button>
            <span className="px-2">
              {page + 1} / {totalPages}
            </span>
            <button
              disabled={page >= totalPages - 1 || loading}
              onClick={() => { setPage(p => p + 1); router.refresh(); }}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
            >
              {t('next')}
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
