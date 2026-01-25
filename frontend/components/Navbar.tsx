'use client';

import Link from 'next/link';
import { useTranslations, useLocale } from 'next-intl';
import { usePathname } from 'next/navigation';
import Image from 'next/image';
import LanguageSwitcher from './LanguageSwitcher';
import ThemeToggle from './ThemeToggle';
import { cn } from '@/lib/utils';

export default function Navbar() {
  const t = useTranslations('app');
  const locale = useLocale();
  const pathname = usePathname();

  const navLinks = [
    { href: `/${locale}/analyze`, key: 'analyze' },
    { href: `/${locale}/glossary`, key: 'glossary' },
    { href: `/${locale}/admin`, key: 'admin' },
  ];

  return (
    <header className="container-px sticky top-0 z-40 backdrop-blur supports-[backdrop-filter]:bg-white/60 supports-[backdrop-filter]:dark:bg-slate-950/60">
      <div className="mx-auto max-w-7xl">
        <nav className="flex items-center justify-between py-4">
          <div className="flex items-center gap-6">
            <Link href={`/${locale}`} className="flex items-center gap-3">
              <Image
                src="/only_flag.png"
                alt="Pride flag logo"
                width={48}
                height={48}
                className="h-10 w-auto sm:h-12"
              />
              <span className="brand-raleway text-slate-800 dark:text-slate-100 text-2xl sm:text-3xl font-extrabold tracking-tight">
                {t('title')}
              </span>
            </Link>
            <div className="hidden md:flex items-center gap-4 text-sm">
              {navLinks.map((link) => {
                const isActive = pathname === link.href;
                return (
                  <Link
                    key={link.key}
                    href={link.href}
                    className={cn(isActive && 'text-pride-purple font-semibold')}
                  >
                    {t(link.key)}
                  </Link>
                );
              })}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            <ThemeToggle />
            {!pathname.includes('/analyze') && (
              <Link href={`/${locale}/analyze`} className="btn-primary hidden sm:inline-flex">
                {t('cta')}
              </Link>
            )}
          </div>
        </nav>
        {pathname !== `/${locale}` && (
          <div className="h-px bg-gradient-to-r from-transparent via-slate-200/60 to-transparent dark:via-slate-800/60" />
        )}
      </div>
    </header>
  );
}
