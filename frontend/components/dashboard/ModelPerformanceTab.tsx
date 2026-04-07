'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, AlertTriangle, GitBranch, Timer, Info } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useModelMetrics } from '@/lib/api/admin';

interface ModelPerformanceTabProps {
  days: number;
  translations: {
    kpis: {
      avgLatency: string;
      errorRate: string;
      fallbackRate: string;
      totalLlmCalls: string;
    };
    modeBreakdown: {
      title: string;
      llm: string;
      hybrid: string;
      rulesOnly: string;
      analyses: string;
    };
    noData: string;
  };
}

function SkeletonLoader({ className }: { className?: string }) {
  return (
    <div className={cn('animate-pulse bg-slate-200 dark:bg-slate-700 rounded', className)} />
  );
}

function Tooltip({ text }: { text: string }) {
  const [visible, setVisible] = useState(false);
  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        className="text-slate-300 hover:text-slate-500 dark:text-slate-600 dark:hover:text-slate-400 transition-colors"
        aria-label="More information"
      >
        <Info className="w-3.5 h-3.5" />
      </button>
      <AnimatePresence>
        {visible && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.15 }}
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-52 rounded-lg bg-slate-800 dark:bg-slate-700 text-white text-xs px-3 py-2 shadow-lg pointer-events-none"
          >
            {text}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800 dark:border-t-slate-700" />
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  );
}

function KpiCard({
  label,
  value,
  sub,
  icon,
  color,
  tooltip,
  isLoading,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ReactNode;
  color: 'sky' | 'green' | 'purple' | 'pink' | 'amber' | 'red';
  tooltip: string;
  isLoading: boolean;
}) {
  const colorConfig: Record<string, string> = {
    sky: 'from-sky-500 to-blue-500',
    green: 'from-green-500 to-emerald-500',
    purple: 'from-purple-500 to-violet-500',
    pink: 'from-pink-500 to-rose-500',
    amber: 'from-amber-500 to-orange-500',
    red: 'from-red-500 to-rose-600',
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9, y: 20 }}
      animate={isLoading ? { opacity: 0, scale: 0.9, y: 20 } : { opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="rounded-xl border bg-white dark:bg-slate-900 p-4 shadow-sm"
    >
      {isLoading ? (
        <div className="space-y-3">
          <SkeletonLoader className="w-10 h-10 rounded-xl" />
          <div>
            <SkeletonLoader className="h-8 w-20 mb-2" />
            <SkeletonLoader className="h-3 w-24" />
          </div>
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between">
            <div className={cn('w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center text-white', colorConfig[color])}>
              {icon}
            </div>
            <Tooltip text={tooltip} />
          </div>
          <div className="mt-3">
            <p className="text-2xl font-bold text-slate-800 dark:text-white">{value}</p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{label}</p>
            {sub && <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{sub}</p>}
          </div>
        </>
      )}
    </motion.div>
  );
}

function ModeBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm">
        <span className="text-slate-700 dark:text-slate-300">{label}</span>
        <span className="text-slate-500 dark:text-slate-400 tabular-nums">
          {count.toLocaleString()} <span className="text-xs">({pct}%)</span>
        </span>
      </div>
      <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
        <motion.div
          className={cn('h-full rounded-full', color)}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

export default function ModelPerformanceTab({ days, translations }: ModelPerformanceTabProps) {
  const { data, isLoading, error } = useModelMetrics(days);

  const fmt = (val: number | null | undefined, suffix = '') =>
    val != null ? `${val.toLocaleString()}${suffix}` : '—';

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label={translations.kpis.avgLatency}
          value={data?.avg_latency_ms != null ? `${(data.avg_latency_ms / 1000).toFixed(2)} s` : '—'}
          sub={data?.min_latency_ms != null && data?.max_latency_ms != null
            ? `${(data.min_latency_ms / 1000).toFixed(2)}–${(data.max_latency_ms / 1000).toFixed(2)} s`
            : undefined}
          icon={<Timer className="w-5 h-5" />}
          color="sky"
          tooltip="Average time the AI model takes to analyze a single sentence. Sub-label shows the min–max range across all requests."
          isLoading={isLoading}
        />
        <KpiCard
          label={translations.kpis.errorRate}
          value={fmt(data?.error_rate, '%')}
          icon={<AlertTriangle className="w-5 h-5" />}
          color={data && data.error_rate > 10 ? 'red' : 'amber'}
          tooltip="Percentage of AI model calls that failed (timeouts, HTTP errors, or circuit-breaker trips). Lower is better."
          isLoading={isLoading}
        />
        <KpiCard
          label={translations.kpis.fallbackRate}
          value={fmt(data?.fallback_rate, '%')}
          icon={<GitBranch className="w-5 h-5" />}
          color="purple"
          tooltip="Percentage of analyses that fell back to rule-based detection (hybrid or rules-only mode) because the AI model was unavailable."
          isLoading={isLoading}
        />
        <KpiCard
          label={translations.kpis.totalLlmCalls}
          value={fmt(data?.total_llm_calls)}
          sub={data ? `${data.total_errors} errors` : undefined}
          icon={<Cpu className="w-5 h-5" />}
          color="green"
          tooltip="Total number of individual sentence-level AI model calls made in the selected time period."
          isLoading={isLoading}
        />
      </div>

      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400 text-sm">
          Failed to load model metrics. Please try again.
        </div>
      )}

      {/* Mode Breakdown */}
      <div className="rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
        <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2 mb-4">
          <Cpu className="w-4 h-4 text-pride-purple" />
          {translations.modeBreakdown.title}
        </h3>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-2">
                <div className="flex justify-between">
                  <SkeletonLoader className="h-4 w-24" />
                  <SkeletonLoader className="h-4 w-16" />
                </div>
                <SkeletonLoader className="h-2 w-full rounded-full" />
              </div>
            ))}
          </div>
        ) : !data || data.total_analyses === 0 ? (
          <p className="text-sm text-slate-500 dark:text-slate-400 py-4 text-center">
            {translations.noData}
          </p>
        ) : (
          <div className="space-y-4">
            <ModeBar
              label={translations.modeBreakdown.llm}
              count={data.mode_llm}
              total={data.total_analyses}
              color="bg-sky-500"
            />
            <ModeBar
              label={translations.modeBreakdown.hybrid}
              count={data.mode_hybrid}
              total={data.total_analyses}
              color="bg-purple-500"
            />
            <ModeBar
              label={translations.modeBreakdown.rulesOnly}
              count={data.mode_rules_only}
              total={data.total_analyses}
              color="bg-amber-500"
            />
            <p className="text-xs text-slate-400 dark:text-slate-500 pt-1">
              {data.total_analyses.toLocaleString()} {translations.modeBreakdown.analyses}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
