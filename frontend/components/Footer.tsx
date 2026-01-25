'use client';

import { useTranslations } from 'next-intl';

export default function Footer() {
  const t = useTranslations('app');

  return (
    <footer className="container-px mt-auto py-4">
      <div className="mx-auto max-w-7xl border-t border-slate-200/60 dark:border-slate-800/60 pt-4 text-sm text-slate-500 dark:text-slate-400">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} {t('footerCopyright')}</p>
          <p className="opacity-80">{t('footerTagline')}</p>
        </div>
      </div>
    </footer>
  );
}
