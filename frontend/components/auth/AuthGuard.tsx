'use client';

import { useAuth } from '@/contexts/AuthContext';
import { notFound } from 'next/navigation';
import { useRouter } from '@/i18n/navigation';
import { useEffect, ReactNode } from 'react';

interface AdminGuardProps {
  children: ReactNode;
}

export function AuthGuard({ children }: AdminGuardProps) {
  const { user, isLoading } = useAuth();
  // Locale-aware router: it applies the correct prefix per `as-needed`
  // (no `/en`, `/he/...` for Hebrew) so we don't hardcode the locale.
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      // Preserve where the user was headed so login can return them there.
      const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
      router.push(`/login?returnUrl=${returnUrl}`);
    }
  }, [isLoading, user, router]);

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

  useEffect(() => {
    // Logged out (e.g. logging out while on the admin page) → landing page,
    // not a 404. The 404 below is reserved for logged-in non-admins.
    if (!isLoading && !user) {
      router.push('/');
    }
  }, [isLoading, user, router]);

  // Spinner while checking auth state or while redirecting a signed-out user.
  if (isLoading || !user) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pride-purple" />
      </div>
    );
  }

  // Per CONTEXT.md: 404 for logged-in non-admins (hide the route's existence).
  if (user.role !== 'site_admin') {
    notFound();
  }

  return <>{children}</>;
}
