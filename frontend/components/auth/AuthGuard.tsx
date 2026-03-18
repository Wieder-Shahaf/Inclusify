'use client';

import { useAuth } from '@/contexts/AuthContext';
import { notFound } from 'next/navigation';
import { ReactNode } from 'react';

interface AdminGuardProps {
  children: ReactNode;
}

export function AdminGuard({ children }: AdminGuardProps) {
  const { user, isLoading } = useAuth();

  // Show nothing while checking auth state (prevents flash)
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pride-purple" />
      </div>
    );
  }

  // Per CONTEXT.md: 404 for non-admins, not redirect
  if (!user || user.role !== 'site_admin') {
    notFound();
  }

  return <>{children}</>;
}
