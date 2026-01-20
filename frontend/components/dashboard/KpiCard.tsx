import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

type Change = {
  value: number; // percentage, can be negative
  since: string;
};

export default function KpiCard({
  label,
  value,
  icon,
  change,
  accent = 'indigo',
  bgColor,
  compact = false,
}: {
  label: string;
  value: string;
  icon?: ReactNode;
  change?: Change;
  accent?: 'indigo' | 'purple' | 'green' | 'amber' | 'rose' | 'sky';
  bgColor?: string;
  compact?: boolean;
}) {
  const up = (change?.value ?? 0) >= 0;
  const accentBg = {
    indigo: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-200',
    purple: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-200',
    green: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-200',
    amber: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-200',
    rose: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-200',
    sky: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-200',
  }[accent];

  return (
    <div
      className={cn(
        'rounded-xl border glass',
        compact ? 'p-3' : 'p-5 sm:p-6 rounded-2xl'
      )}
      style={bgColor ? { backgroundColor: bgColor } : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className={cn('text-slate-500 dark:text-slate-400', compact ? 'text-xs' : 'text-sm')}>
            {label}
          </p>
          <p className={cn('font-black tracking-tight', compact ? 'mt-1 text-xl' : 'mt-2 text-3xl')}>
            {value}
          </p>
        </div>
        {icon ? (
          <div className={cn('grid place-items-center rounded-lg', accentBg, compact ? 'h-8 w-8' : 'h-11 w-11 rounded-xl')}>
            {icon}
          </div>
        ) : null}
      </div>
      {change && (
        <p
          className={cn(
            'font-medium',
            compact ? 'mt-1.5 text-xs' : 'mt-3 text-sm',
            up ? 'text-green-600 dark:text-green-400' : 'text-rose-600 dark:text-rose-400'
          )}
        >
          {up ? '+' : ''}
          {change.value}% {compact ? '' : 'from '}{change.since}
        </p>
      )}
    </div>
  );
}
