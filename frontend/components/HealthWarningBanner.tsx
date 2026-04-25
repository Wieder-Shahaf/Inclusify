'use client';

import { AlertTriangle, Info } from 'lucide-react';
import Link from 'next/link';

interface HealthWarningBannerProps {
  message: string;
  variant?: 'error' | 'info';
  linkHref?: string;
  linkText?: string;
}

export default function HealthWarningBanner({ message, variant = 'error', linkHref, linkText }: HealthWarningBannerProps) {
  const isInfo = variant === 'info';
  return (
    <div
      className={
        isInfo
          ? 'fixed top-16 left-0 right-0 z-50 bg-sky-50 dark:bg-sky-900/80 border-b border-sky-200 dark:border-sky-700 px-4 py-2 shadow-sm'
          : 'fixed top-16 left-0 right-0 z-50 bg-amber-50 dark:bg-amber-900/80 border-b border-amber-200 dark:border-amber-700 px-4 py-2 shadow-sm'
      }
    >
      <div className={`max-w-7xl mx-auto flex items-center gap-2 text-sm ${isInfo ? 'text-sky-700 dark:text-sky-300' : 'text-amber-700 dark:text-amber-300'}`}>
        {isInfo
          ? <Info className="w-4 h-4 flex-shrink-0" />
          : <AlertTriangle className="w-4 h-4 flex-shrink-0" />
        }
        <span>{message}</span>
        {linkHref && linkText && (
          <Link
            href={linkHref}
            className={`ml-1 underline underline-offset-2 font-medium hover:opacity-80 transition-opacity ${isInfo ? 'text-sky-700 dark:text-sky-400' : 'text-amber-700 dark:text-amber-400'}`}
          >
            {linkText}
          </Link>
        )}
      </div>
    </div>
  );
}
