'use client';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, ChevronDown, ChevronUp, MessageSquareWarning } from 'lucide-react';
import { useTranslations, useLocale } from 'next-intl';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { useAdminFeedback, useAdminFrequencyTrends } from '@/lib/api/admin';

interface FrequencyTrendsCardProps {
  days: number;
}

const WS_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/^http/, 'ws');

export default function FrequencyTrendsCard({ days }: FrequencyTrendsCardProps) {
  const t = useTranslations('admin.frequencyTrends');
  const locale = useLocale();
  const { data, isLoading, error, refresh } = useAdminFrequencyTrends(days);
  const { data: feedbackData } = useAdminFeedback(1, 1);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const token = localStorage.getItem('auth_token');
    if (!token) return;

    // TODO(security): The browser WebSocket API does not support custom headers on the
    // initial handshake, so the JWT is passed as a URL query parameter. Tokens in URLs
    // are logged by web servers, proxies, CDNs, and browser history. Medium-term fix:
    // implement a /api/v1/admin/ws-ticket endpoint that issues a single-use, short-TTL
    // ticket and pass that in the URL instead of the full long-lived JWT.
    const ws = new WebSocket(`${WS_BASE_URL}/api/v1/admin/ws?token=${encodeURIComponent(token)}`);
    ws.onopen = () => setWsConnected(true);
    ws.onclose = (ev) => {
      setWsConnected(false);
      if (ev.code === 4001) {
        window.location.href = `/${locale}/login`;
      }
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.event === 'new_analysis') refresh();
      } catch { /* ignore */ }
    };
    return () => { ws.close(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locale]);

  const trends = data?.trends || [];
  const isRtl = locale === 'he';
  const maxCount = Math.max(...trends.map((trend) => trend.count), 1);
  const totalCount = trends.reduce((sum, trend) => sum + trend.count, 0);
  const accentStyles = [
    'bg-rose-500',
    'bg-amber-500',
    'bg-purple-500',
    'bg-sky-500',
    'bg-emerald-500',
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border bg-white dark:bg-slate-900 p-4 shadow-sm"
      style={{ width: '100%', minWidth: 0, boxSizing: 'border-box' }}
    >
      <div className="mb-2 flex shrink-0 items-center justify-between">
        <div>
          <h3 className="font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-pride-purple" />
            {t('title')}
            <span
              className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-400 animate-pulse' : 'bg-slate-300'}`}
              aria-label={wsConnected ? 'Live updates connected' : 'Live updates disconnected'}
              role="status"
            />
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{t('subtitle')}</p>
        </div>
      </div>

      {isLoading ? (
        <div className="min-h-0 flex-1 space-y-3 overflow-hidden">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse bg-slate-200 dark:bg-slate-700 rounded h-8" />
          ))}
        </div>
      ) : error ? (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400 text-sm">
          Failed to load trends. Please try again.
        </div>
      ) : trends.length === 0 ? (
        <div className="p-8 text-center text-slate-500 dark:text-slate-400">{t('noData')}</div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden">
          <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-0.5">
            {trends.slice(0, 5).map((tr, index) => {
              const isOpen = expanded === tr.category;
              const pctOfTotal = totalCount > 0 ? Math.round((tr.count / totalCount) * 100) : 0;
              const barWidth = Math.max(6, Math.round((tr.count / maxCount) * 100));
              return (
                <div
                  key={tr.category}
                  className="relative rounded-lg border border-slate-200 bg-white p-2.5 dark:border-slate-700 dark:bg-slate-900"
                >
                  <button
                    type="button"
                    onClick={() => setExpanded(isOpen ? null : tr.category)}
                    aria-expanded={isOpen}
                    dir={isRtl ? 'rtl' : 'ltr'}
                    className="flex w-full items-center gap-3 text-left text-sm"
                  >
                    <span className="flex items-center gap-2 text-xs text-slate-500 shrink-0">
                      {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center justify-between gap-3">
                        <span className="truncate font-semibold text-slate-700 dark:text-slate-200" style={{ textAlign: isRtl ? 'right' : 'left' }}>
                          {tr.category}
                        </span>
                        <span className="shrink-0 tabular-nums text-slate-500 dark:text-slate-400">
                          {tr.count.toLocaleString()} <span className="text-xs">({pctOfTotal}%)</span>
                        </span>
                      </span>
                      <span className="mt-2 block h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                        <span
                          className={cn('block h-full rounded-full', accentStyles[index % accentStyles.length])}
                          style={{ width: `${barWidth}%` }}
                        />
                      </span>
                    </span>
                  </button>

                  {isOpen && (
                    <div className="mt-2 max-h-40 overflow-y-auto rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                      <ol dir={isRtl ? 'rtl' : 'ltr'} className="divide-y divide-slate-100 dark:divide-slate-700/50">
                        {tr.top_phrases.map((tp, i) => (
                          <li
                            key={i}
                            className="grid text-xs text-slate-600 dark:text-slate-400 px-3 py-1.5 hover:bg-white dark:hover:bg-slate-800 transition-colors"
                            style={{ gridTemplateColumns: 'auto 1fr', gap: '10px', alignItems: 'center' }}
                          >
                            <span className="text-slate-400 dark:text-slate-500 tabular-nums shrink-0">{tp.count}&times;</span>
                            <span className="truncate">&ldquo;{tp.phrase}&rdquo;</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="mt-auto">
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-slate-600 dark:border-slate-700 dark:bg-slate-800/40 dark:text-slate-300">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide">
                  <MessageSquareWarning className="h-3 w-3" />
                  Feedback For Review
                  <span className="inline-flex items-center justify-center min-w-[1.25rem] h-[1.25rem] rounded-full bg-slate-500 px-1 text-[10px] font-bold text-white tabular-nums">
                    {(feedbackData?.total ?? 0).toLocaleString()}
                  </span>
                </div>
                <Link
                  href={`/${locale}/admin?tab=feedback`}
                  className="text-[10px] font-medium text-slate-500 dark:text-slate-400 hover:underline"
                  onClick={e => e.stopPropagation()}
                >
                  View all →
                </Link>
              </div>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
