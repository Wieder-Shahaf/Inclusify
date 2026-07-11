'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useTranslations, useLocale } from 'next-intl';
import { usePathname } from 'next/navigation';
import Image from 'next/image';
import { Menu, X } from 'lucide-react';
import LanguageSwitcher from './LanguageSwitcher';
import ThemeToggle from './ThemeToggle';
import { useAuth } from '@/contexts/AuthContext';
import { UserDropdown } from '@/components/auth/UserDropdown';
import { cn } from '@/lib/utils';
import ContactModal from '@/components/ContactModal';

export default function Navbar() {
  const t = useTranslations('app');
  const locale = useLocale();
  const pathname = usePathname();
  const { user, isLoading } = useAuth();
  const [contactOpen, setContactOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const tc = useTranslations('contact');

  // Close the mobile menu whenever the route changes. Done during render via a
  // stored-previous-value (React's recommended pattern) rather than an effect,
  // so it also covers navigations not triggered by the menu's own links.
  const [menuPathname, setMenuPathname] = useState(pathname);
  if (pathname !== menuPathname) {
    setMenuPathname(pathname);
    setMenuOpen(false);
  }

  // Filter navLinks - hide dashboard for non-admins.
  // The analyze entry point lives only in the top-right CTA button — no
  // duplicate "Analyze" link on the left.
  const navLinks = [
    { href: `/${locale}/glossary`, key: 'glossary' },
    // Only show dashboard link if user is site_admin
    ...(user?.role === 'site_admin' ? [{ href: `/${locale}/admin`, key: 'admin' }] : []),
  ];

  return (
    <header className="container-px sticky top-0 z-40 backdrop-blur supports-[backdrop-filter]:bg-white/60 supports-[backdrop-filter]:dark:bg-slate-950/60">
      <div className="mx-auto max-w-7xl">
        <nav className="flex items-center justify-between py-4 gap-2">
          <div className="flex items-center gap-6 min-w-0">
            <Link href={`/${locale}`} className="flex items-center gap-2 sm:gap-3 min-w-0">
              <Image
                src="/only_flag.png"
                alt="Pride flag logo"
                width={48}
                height={48}
                className="h-9 w-auto sm:h-12 flex-shrink-0"
              />
              <span className="brand-raleway text-slate-800 dark:text-slate-100 text-xl sm:text-3xl font-extrabold tracking-tight truncate">
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

          {/* Desktop controls */}
          <div className="hidden md:flex items-center gap-3">
            <LanguageSwitcher />
            <ThemeToggle />
            {!isLoading && user && (
              <button
                type="button"
                onClick={() => setContactOpen(true)}
                className="btn-ghost min-h-11 px-3 text-sm"
                aria-haspopup="dialog"
              >
                {tc('button')}
              </button>
            )}
            {!isLoading && (
              <>
                {user ? (
                  <UserDropdown />
                ) : (
                  <Link
                    href={`/${locale}/login`}
                    className="text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-pride-purple transition-colors"
                  >
                    {t('login') || 'Login'}
                  </Link>
                )}
              </>
            )}
            {!pathname.includes('/analyze') && (
              <Link href={`/${locale}/analyze`} className="btn-primary inline-flex">
                {t('cta')}
              </Link>
            )}
          </div>

          {/* Mobile controls: theme toggle stays handy + hamburger */}
          <div className="flex md:hidden items-center gap-1 flex-shrink-0">
            <ThemeToggle />
            <button
              type="button"
              onClick={() => setMenuOpen((o) => !o)}
              className="btn-ghost p-2 rounded-lg"
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={menuOpen}
            >
              {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </nav>

        {/* Mobile menu panel */}
        {menuOpen && (
          <div className="md:hidden border-t border-slate-200/60 dark:border-slate-800/60 py-3 flex flex-col gap-1">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.key}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className={cn(
                    'px-3 py-2.5 rounded-lg text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors',
                    isActive && 'text-pride-purple',
                  )}
                >
                  {t(link.key)}
                </Link>
              );
            })}

            {!isLoading && user && (
              <button
                type="button"
                onClick={() => { setMenuOpen(false); setContactOpen(true); }}
                className="text-start px-3 py-2.5 rounded-lg text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors"
                aria-haspopup="dialog"
              >
                {tc('button')}
              </button>
            )}

            {!isLoading && !user && (
              <Link
                href={`/${locale}/login`}
                onClick={() => setMenuOpen(false)}
                className="px-3 py-2.5 rounded-lg text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors"
              >
                {t('login') || 'Login'}
              </Link>
            )}

            <div className="flex items-center justify-between gap-2 px-3 pt-2 mt-1 border-t border-slate-200/60 dark:border-slate-800/60">
              <LanguageSwitcher />
              {!isLoading && user && <UserDropdown />}
            </div>

            {!pathname.includes('/analyze') && (
              <Link
                href={`/${locale}/analyze`}
                onClick={() => setMenuOpen(false)}
                className="btn-primary mt-2 justify-center"
              >
                {t('cta')}
              </Link>
            )}
          </div>
        )}

        {pathname !== `/${locale}` && !menuOpen && (
          <div className="h-px bg-gradient-to-r from-transparent via-slate-200/60 to-transparent dark:via-slate-800/60" />
        )}
      </div>
      <ContactModal open={contactOpen} onClose={() => setContactOpen(false)} />
    </header>
  );
}
