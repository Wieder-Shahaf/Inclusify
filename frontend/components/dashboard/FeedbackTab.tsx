'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  ThumbsUp,
  ThumbsDown,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
  BarChart2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAdminFeedback } from '@/lib/api/admin';

interface FeedbackTabProps {
  translations: {
    title: string;
    filterAll: string;
    filterUp: string;
    filterDown: string;
    colVote: string;
    colFlaggedText: string;
    colSeverity: string;
    colUser: string;
    colDate: string;
    colComment: string;
    noData: string;
    helpful: string;
    falsePositive: string;
    anonymous: string;
  };
}

const SEVERITY_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  outdated:              { bg: 'bg-sky-100 dark:bg-sky-900/30',   text: 'text-sky-700 dark:text-sky-300',   label: 'Outdated' },
  biased:                { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-300', label: 'Biased' },
  potentially_offensive: { bg: 'bg-rose-100 dark:bg-rose-900/30',  text: 'text-rose-700 dark:text-rose-300',  label: 'Offensive' },
  factually_incorrect:   { bg: 'bg-red-100 dark:bg-red-900/30',    text: 'text-red-700 dark:text-red-300',    label: 'Factual' },
  low:    { bg: 'bg-sky-100 dark:bg-sky-900/30',   text: 'text-sky-700 dark:text-sky-300',   label: 'Low' },
  medium: { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-300', label: 'Medium' },
  high:   { bg: 'bg-rose-100 dark:bg-rose-900/30',  text: 'text-rose-700 dark:text-rose-300',  label: 'High' },
};

function SkeletonRow() {
  return (
    <tr className="border-b border-slate-100 dark:border-slate-800">
      {[128, 192, 96, 160, 112, 144].map((w, i) => (
        <td key={i} className="px-4 py-4">
          <div
            className="h-4 animate-pulse bg-slate-200 dark:bg-slate-700 rounded"
            style={{ width: w }}
          />
        </td>
      ))}
    </tr>
  );
}

interface KpiCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  accent: string;
}
function KpiCard({ icon, label, value, sub, accent }: KpiCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm flex items-center gap-4"
    >
      <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center shrink-0', accent)}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-slate-800 dark:text-white leading-tight">{value}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </motion.div>
  );
}

export default function FeedbackTab({ translations: t }: FeedbackTabProps) {
  const [page, setPage] = useState(1);
  const [voteFilter, setVoteFilter] = useState<'up' | 'down' | undefined>(undefined);

  const { data, isLoading, error } = useAdminFeedback(page, 20, voteFilter);

  const handleFilterChange = (filter: 'up' | 'down' | undefined) => {
    setVoteFilter(filter);
    setPage(1);
  };

  const totalAll         = (data?.total_helpful ?? 0) + (data?.total_false_positive ?? 0);
  const helpfulPct       = totalAll > 0 ? Math.round(((data?.total_helpful ?? 0) / totalAll) * 100) : 0;
  const falsePct         = totalAll > 0 ? Math.round(((data?.total_false_positive ?? 0) / totalAll) * 100) : 0;

  return (
    <div className="space-y-6">

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <KpiCard
          icon={<BarChart2 className="w-6 h-6 text-pride-purple" />}
          label="Total Votes"
          value={isLoading ? '—' : totalAll}
          sub="all time"
          accent="bg-purple-50 dark:bg-purple-900/20"
        />
        <KpiCard
          icon={<ThumbsUp className="w-6 h-6 text-green-600 dark:text-green-400" />}
          label={t.filterUp}
          value={isLoading ? '—' : `${data?.total_helpful ?? 0}`}
          sub={totalAll > 0 ? `${helpfulPct}% of votes` : 'no votes yet'}
          accent="bg-green-50 dark:bg-green-900/20"
        />
        <KpiCard
          icon={<ThumbsDown className="w-6 h-6 text-rose-600 dark:text-rose-400" />}
          label={t.filterDown}
          value={isLoading ? '—' : `${data?.total_false_positive ?? 0}`}
          sub={totalAll > 0 ? `${falsePct}% of votes` : 'no votes yet'}
          accent="bg-rose-50 dark:bg-rose-900/20"
        />
      </div>

      {/* Sentiment bar */}
      {totalAll > 0 && (
        <div className="rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Overall Sentiment</p>
            <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
              <span className="flex items-center gap-1"><ThumbsUp className="w-3 h-3 text-green-500" /> {helpfulPct}% helpful</span>
              <span className="flex items-center gap-1"><ThumbsDown className="w-3 h-3 text-rose-500" /> {falsePct}% false detection</span>
            </div>
          </div>
          <div className="flex h-3 rounded-full overflow-hidden gap-0.5">
            <div
              className="bg-green-400 dark:bg-green-500 transition-all duration-500 rounded-l-full"
              style={{ width: `${helpfulPct}%` }}
            />
            <div
              className="bg-rose-400 dark:bg-rose-500 transition-all duration-500 rounded-r-full"
              style={{ width: `${falsePct}%` }}
            />
          </div>
        </div>
      )}

      {/* Filter bar + table */}
      <div className="rounded-2xl border bg-white dark:bg-slate-900 shadow-sm overflow-hidden">

        {/* Table header row */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-pride-purple" />
            <h3 className="font-semibold text-slate-800 dark:text-white">{t.title}</h3>
            {data && (
              <span className="ml-1 text-sm text-slate-400">({data.total})</span>
            )}
          </div>

          {/* Filter pills */}
          <div className="flex items-center gap-2">
            {([
              { key: undefined,  label: t.filterAll,  icon: null },
              { key: 'up'  as const, label: t.filterUp,   icon: <ThumbsUp  className="w-3.5 h-3.5" /> },
              { key: 'down' as const, label: t.filterDown, icon: <ThumbsDown className="w-3.5 h-3.5" /> },
            ]).map(({ key, label, icon }) => (
              <button
                key={String(key)}
                onClick={() => handleFilterChange(key)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all border',
                  voteFilter === key
                    ? key === 'up'
                      ? 'bg-green-50 border-green-300 text-green-700 dark:bg-green-900/20 dark:border-green-600 dark:text-green-300'
                      : key === 'down'
                        ? 'bg-rose-50 border-rose-300 text-rose-700 dark:bg-rose-900/20 dark:border-rose-600 dark:text-rose-300'
                        : 'bg-slate-100 border-slate-300 text-slate-700 dark:bg-slate-700 dark:border-slate-500 dark:text-slate-200'
                    : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-400',
                )}
              >
                {icon}
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <table className="w-full text-sm">
            <tbody>{[1,2,3,4,5].map(i => <SkeletonRow key={i} />)}</tbody>
          </table>
        ) : error ? (
          <div className="p-10 text-center text-red-500 dark:text-red-400 text-sm">
            Failed to load feedback — check backend logs.
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="py-16 flex flex-col items-center gap-3 text-slate-400 dark:text-slate-500">
            <MessageSquare className="w-10 h-10 opacity-30" />
            <p className="text-sm font-medium">{t.noData}</p>
            <p className="text-xs text-center max-w-xs">
              Feedback appears here once users click the 👍 / 👎 buttons on analysis flags.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-semibold text-slate-500 dark:text-slate-400 bg-slate-50/70 dark:bg-slate-800/40 border-b border-slate-100 dark:border-slate-800">
                  <th className="px-6 py-3 w-20">{t.colVote}</th>
                  <th className="px-4 py-3">{t.colFlaggedText}</th>
                  <th className="px-4 py-3 w-36">{t.colSeverity}</th>
                  <th className="px-4 py-3 w-44">{t.colUser}</th>
                  <th className="px-4 py-3 w-32">{t.colDate}</th>
                  <th className="px-4 py-3">{t.colComment}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 dark:divide-slate-800/50">
                {data.items.map((item, idx) => {
                  const sev = item.severity ? (SEVERITY_STYLES[item.severity] ?? null) : null;
                  return (
                    <motion.tr
                      key={item.feedback_id}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.02 }}
                      className="hover:bg-slate-50/60 dark:hover:bg-slate-800/20 transition-colors"
                    >
                      {/* Vote icon */}
                      <td className="px-6 py-4">
                        {item.vote === 'up' ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700 dark:bg-green-900/25 dark:text-green-300 border border-green-200 dark:border-green-800">
                            <ThumbsUp className="w-3 h-3" />
                            {t.helpful}
                          </span>
                        ) : item.vote === 'down' ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-50 text-rose-700 dark:bg-rose-900/25 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
                            <ThumbsDown className="w-3 h-3" />
                            {t.falsePositive}
                          </span>
                        ) : (
                          <span className="text-slate-300 dark:text-slate-600">—</span>
                        )}
                      </td>

                      {/* Flagged text */}
                      <td className="px-4 py-4 max-w-xs">
                        {item.flagged_text ? (
                          <span className="font-medium text-slate-800 dark:text-slate-100 break-words">
                            &ldquo;{item.flagged_text}&rdquo;
                          </span>
                        ) : (
                          <span className="text-slate-300 dark:text-slate-600 italic text-xs">no text</span>
                        )}
                      </td>

                      {/* Severity */}
                      <td className="px-4 py-4">
                        {sev ? (
                          <span className={cn('px-2.5 py-1 rounded-full text-xs font-medium capitalize', sev.bg, sev.text)}>
                            {sev.label}
                          </span>
                        ) : (
                          <span className="text-slate-300 dark:text-slate-600">—</span>
                        )}
                      </td>

                      {/* User */}
                      <td className="px-4 py-4">
                        {item.user_email === 'anonymous' ? (
                          <span className="text-xs italic text-slate-400">{t.anonymous}</span>
                        ) : (
                          <span className="text-slate-600 dark:text-slate-300 text-xs truncate block max-w-[160px]" title={item.user_email}>
                            {item.user_email}
                          </span>
                        )}
                      </td>

                      {/* Date */}
                      <td className="px-4 py-4 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                        {new Date(item.created_at).toLocaleDateString(undefined, {
                          day: 'numeric', month: 'short', year: 'numeric',
                        })}
                        <br />
                        <span className="text-slate-400 dark:text-slate-500">
                          {new Date(item.created_at).toLocaleTimeString(undefined, {
                            hour: '2-digit', minute: '2-digit',
                          })}
                        </span>
                      </td>

                      {/* Comment */}
                      <td className="px-4 py-4 max-w-xs">
                        {item.comment ? (
                          <span className="text-slate-500 dark:text-slate-400 text-xs break-words">{item.comment}</span>
                        ) : (
                          <span className="text-slate-200 dark:text-slate-700">—</span>
                        )}
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20">
            <span className="text-sm text-slate-500 dark:text-slate-400">
              Page {data.page} of {data.total_pages} &nbsp;·&nbsp; {data.total} total
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded-lg border bg-white dark:bg-slate-800 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                disabled={page === data.total_pages}
                className="p-2 rounded-lg border bg-white dark:bg-slate-800 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
