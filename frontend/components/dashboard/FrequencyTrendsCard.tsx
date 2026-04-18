'use client';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { BarChart3, ChevronDown, ChevronUp } from 'lucide-react';
import { useTranslations, useLocale } from 'next-intl';
import { useAdminFrequencyTrends } from '@/lib/api/admin';
import SimpleBarChart from './SimpleBarChart';

interface FrequencyTrendsCardProps {
  days: number;
}

const WS_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/^http/, 'ws');

export default function FrequencyTrendsCard({ days }: FrequencyTrendsCardProps) {
  const t = useTranslations('admin.frequencyTrends');
  const locale = useLocale();
  const { data, isLoading, error, refresh } = useAdminFrequencyTrends(days);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const token = localStorage.getItem('auth_token');
    if (!token) return;

    const ws = new WebSocket(`${WS_BASE_URL}/api/v1/admin/ws?token=${encodeURIComponent(token)}`);
    ws.onopen = () => setWsConnected(true);
    ws.onclose = (ev) => {
      setWsConnected(false);
      if (ev.code === 4001) {
        // Token expired or invalid — redirect to login
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

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-2xl border bg-white dark:bg-slate-900 p-6 shadow-sm"
    >
      <div className="flex items-center justify-between mb-4">
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
        <div className="space-y-3">
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
        <>
          <SimpleBarChart
            data={trends.map((tr) => tr.count)}
            labels={trends.map((tr) => tr.category)}
          />
          <div className="mt-4 space-y-2">
            {trends.map((tr) => {
              const isOpen = expanded === tr.category;
              return (
                <div key={tr.category} className="border border-slate-200 dark:border-slate-700 rounded-lg">
                  <button
                    type="button"
                    onClick={() => setExpanded(isOpen ? null : tr.category)}
                    className="w-full flex items-center justify-between px-3 py-2 text-sm"
                    aria-expanded={isOpen}
                  >
                    <span className="font-medium text-slate-700 dark:text-slate-200">{tr.category}</span>
                    <span className="flex items-center gap-2 text-xs text-slate-500">
                      <span className="bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">{tr.count}</span>
                      {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </span>
                  </button>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        <ol className="px-4 py-2 space-y-1 text-xs text-slate-600 dark:text-slate-400">
                          {tr.top_phrases.map((tp, i) => (
                            <li key={i}>&ldquo;{tp.phrase}&rdquo; &times; {tp.count}</li>
                          ))}
                        </ol>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        </>
      )}
    </motion.div>
  );
}
