'use client';

import { useLocale } from 'next-intl';
import { useRouter, usePathname } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { useTransition } from 'react';

export default function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  const switchLocale = (newLocale: 'en' | 'he') => {
    if (newLocale === locale) return;

    startTransition(() => {
      router.replace(pathname, { locale: newLocale });
    });
  };

  return (
    <div className={cn(
      "inline-flex rounded-lg border border-slate-200 dark:border-slate-800 overflow-hidden",
      isPending && "opacity-50 pointer-events-none"
    )}>
      <button
        onClick={() => switchLocale('en')}
        className={cn(
          'px-3 py-1.5 text-sm font-medium transition-colors',
          locale === 'en'
            ? 'bg-pride-purple/10 text-pride-purple'
            : 'hover:bg-slate-100 dark:hover:bg-slate-800'
        )}
        aria-pressed={locale === 'en'}
        disabled={isPending}
      >
        EN
      </button>
      <button
        onClick={() => switchLocale('he')}
        className={cn(
          'px-3 py-1.5 text-sm font-medium transition-colors',
          locale === 'he'
            ? 'bg-pride-purple/10 text-pride-purple'
            : 'hover:bg-slate-100 dark:hover:bg-slate-800'
        )}
        aria-pressed={locale === 'he'}
        disabled={isPending}
      >
        עב
      </button>
    </div>
  );
}
