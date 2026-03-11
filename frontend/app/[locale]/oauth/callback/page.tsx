'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useLocale } from 'next-intl';
import { toast } from 'sonner';

// Force dynamic rendering to allow useSearchParams without prerender error
export const dynamic = 'force-dynamic';

function OAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const locale = useLocale();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      // Check for error in URL params (OAuth failure)
      const errorParam = searchParams.get('error');
      if (errorParam) {
        setError('OAuth authentication failed. Please try again.');
        toast.error('OAuth authentication failed');
        setTimeout(() => router.push(`/${locale}/login`), 2000);
        return;
      }

      // Get token from URL (backend redirects with token in URL or cookie)
      const token = searchParams.get('access_token');

      if (token) {
        // Store token in localStorage
        localStorage.setItem('auth_token', token);

        // Set 30-day expiry for OAuth logins
        const expiry = new Date();
        expiry.setDate(expiry.getDate() + 30);
        localStorage.setItem('auth_token_expiry', expiry.toISOString());

        toast.success('Successfully signed in with Google!');

        // Get stored return URL or default to home
        const returnUrl = localStorage.getItem('auth_return_url') || `/${locale}`;
        localStorage.removeItem('auth_return_url');

        // Force page reload to pick up new auth state
        window.location.href = returnUrl;
      } else {
        // If no token in URL, check if backend set a cookie and redirect
        // The backend may handle token storage differently
        const returnUrl = localStorage.getItem('auth_return_url') || `/${locale}`;
        localStorage.removeItem('auth_return_url');
        window.location.href = returnUrl;
      }
    };

    handleCallback();
  }, [searchParams, router, locale]);

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center py-12">
        <div className="text-center">
          <p className="text-red-500 mb-4">{error}</p>
          <p className="text-slate-600 dark:text-slate-400">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex items-center justify-center py-12">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pride-purple mx-auto mb-4" />
        <p className="text-slate-600 dark:text-slate-400">Completing sign in...</p>
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex-1 flex items-center justify-center py-12">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pride-purple mx-auto mb-4" />
        <p className="text-slate-600 dark:text-slate-400">Loading...</p>
      </div>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <OAuthCallbackContent />
    </Suspense>
  );
}
