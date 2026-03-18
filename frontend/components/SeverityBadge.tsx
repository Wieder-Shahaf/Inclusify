'use client';

import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';

export type Severity = 'outdated' | 'biased' | 'potentially_offensive' | 'factually_incorrect';

export default function SeverityBadge({ level }: { level: Severity }) {
  const t = useTranslations('severity');

  const color = {
    outdated: 'bg-sky-100 text-sky-900 dark:bg-sky-900/40 dark:text-sky-100',
    biased: 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100',
    potentially_offensive: 'bg-rose-100 text-rose-900 dark:bg-rose-900/40 dark:text-rose-100',
    factually_incorrect: 'bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-100',
  }[level];

  return <span className={cn('badge', color)}>{t(level)}</span>;
}
