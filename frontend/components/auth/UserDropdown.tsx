'use client';

import { useState, useEffect, useRef } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { LogOut, User, History, X } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { UserAvatar } from './UserAvatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

const hintKey = (userId: string) => `profile_hint_${userId}`;

export function UserDropdown() {
  const t = useTranslations('auth');
  const tNav = useTranslations('app');
  const locale = useLocale();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [showHint, setShowHint] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const profileIncomplete = !!user && (!user.full_name || !user.institution || !user.profession);

  // Show hint once per login session: key is per-user and cleared on logout
  useEffect(() => {
    if (!user || !profileIncomplete) return;
    const key = hintKey(user.id);
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, '1');
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setShowHint(true);
    timerRef.current = setTimeout(() => setShowHint(false), 7000);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [user?.id, profileIncomplete]); // eslint-disable-line react-hooks/exhaustive-deps

  const dismissHint = () => {
    setShowHint(false);
    if (timerRef.current) clearTimeout(timerRef.current);
  };

  const handleLogout = () => {
    if (user) sessionStorage.removeItem(hintKey(user.id));
    logout();
    router.push(`/${locale}`);
  };

  if (!user) return null;

  return (
    <div className="relative">
      {showHint && (
        <div className="absolute right-0 top-12 z-50 w-64 rounded-xl bg-white dark:bg-slate-800 shadow-lg border border-slate-200 dark:border-slate-700 p-4 animate-in fade-in slide-in-from-top-2 duration-300">
          <button
            onClick={dismissHint}
            className="absolute top-2 right-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            aria-label="Dismiss"
          >
            <X className="w-3.5 h-3.5" />
          </button>
          <p className="text-sm text-slate-700 dark:text-slate-200 leading-snug pr-4">
            👋 Welcome! Take a moment to{' '}
            <Link
              href={`/${locale}/profile`}
              onClick={dismissHint}
              className="font-semibold text-pride-purple underline underline-offset-2 hover:text-pride-purple/80"
            >
              complete your profile
            </Link>
            {' '}so we can personalize your experience.
          </p>
          <div className="absolute -top-2 right-4 w-3 h-3 rotate-45 bg-white dark:bg-slate-800 border-l border-t border-slate-200 dark:border-slate-700" />
        </div>
      )}

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className="relative flex items-center gap-2 rounded-full focus:outline-none focus:ring-2 focus:ring-pride-purple focus:ring-offset-2"
            aria-label="User menu"
          >
            <UserAvatar email={user.email} />
            {profileIncomplete && (
              <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-amber-400 rounded-full border-2 border-white dark:border-slate-900 animate-pulse" aria-hidden="true" />
            )}
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              {user.full_name && (
                <p className="text-sm font-medium">{user.full_name}</p>
              )}
              <p className={user.full_name ? 'text-xs text-slate-500 dark:text-slate-400' : 'text-sm font-medium'}>{user.email}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 capitalize">{user.role}</p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link href={`/${locale}/profile`} className="flex items-center gap-2 cursor-pointer">
              <User className="w-4 h-4" />
              <span>{tNav('profile') || 'Profile'}</span>
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href={`/${locale}/history`} className="flex items-center gap-2 cursor-pointer">
              <History className="w-4 h-4" />
              <span>{tNav('myAnalyses') || 'My Analyses'}</span>
            </Link>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onClick={handleLogout}
            className="flex items-center gap-2 cursor-pointer text-red-600 dark:text-red-400 focus:text-red-700 dark:focus:text-red-300"
          >
            <LogOut className="w-4 h-4" />
            <span>{t('logout') || 'Logout'}</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
