'use client';

import { useAuth } from '@/contexts/AuthContext';
import { notFound, useRouter } from 'next/navigation';
import { useLocale } from 'next-intl';
import { useEffect, ReactNode } from 'react';

interface AdminGuardProps {
  children: ReactNode;
}

export function AuthGuard({ children }: AdminGuardProps) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const locale = useLocale();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push(`/${locale}/login`);
    }
  }, [isLoading, user, router, locale]);

  if (isLoading || !user) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pride-purple" />
      </div>
    );
  }

  return <>{children}</>;
}

export function AdminGuard({ children }: AdminGuardProps) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const locale = useLocale();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push(`/${locale}/login`);
    }
  }, [isLoading, user, router, locale]);

  if (isLoading || !user) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pride-purple" />
      </div>
    );
  }

  // Per CONTEXT.md: 404 for logged-in non-admins
  if (user.role !== 'site_admin') {
    notFound();
  }

  return <>{children}</>;
}
