'use client';

import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';

export type Severity = 'outdated' | 'biased' | 'offensive' | 'incorrect';

export default function SeverityBadge({ level }: { level: Severity }) {
  const t = useTranslations('severity');

  // Colors verified with WebAIM Contrast Checker for WCAG AA 4.5:1 compliance
  // Light mode: dark text on light background
  // Dark mode: light text on semi-transparent dark background
  const color = {
    outdated: 'bg-sky-100 text-sky-900 dark:bg-sky-900/40 dark:text-sky-100',
    biased: 'bg-amber-100 text-amber-900 dark:bg-amber-900/40 dark:text-amber-100',
    offensive: 'bg-rose-100 text-rose-900 dark:bg-rose-900/40 dark:text-rose-100',
    incorrect: 'bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-100',
  }[level];

  return <span className={cn('badge', color)}>{t(level)}</span>;
}
