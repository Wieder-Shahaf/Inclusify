'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { forgotPassword } from '@/lib/api/auth';

const schema = z.object({
  email: z.string().min(1, 'emailRequired').email('emailInvalid'),
});

type FormData = z.infer<typeof schema>;

type State = 'idle' | 'sent' | 'not_found' | 'oauth_user';

export function ForgotPasswordForm({ locale }: { locale: string }) {
  const t = useTranslations('auth');
  const tv = useTranslations('auth.validation');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [state, setState] = useState<State>('idle');

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    try {
      await forgotPassword(data.email);
      setState('sent');
    } catch (error) {
      const detail = error instanceof Error ? error.message : '';
      if (detail === 'EMAIL_NOT_FOUND') {
        setState('not_found');
      } else if (detail === 'OAUTH_USER') {
        setState('oauth_user');
      } else {
        setState('sent'); // fallback: don't expose unexpected errors
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (state === 'sent') {
    return (
      <div className="w-full max-w-md mx-auto">
        <div className="glass p-8 rounded-2xl text-center">
          <div className="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2">{t('resetLinkSent')}</h2>
          <p className="text-slate-600 dark:text-slate-400 mb-6">{t('resetLinkSentDescription')}</p>
          <Link href={`/${locale}/login`} className="text-pride-purple hover:underline font-medium">
            {t('backToLogin')}
          </Link>
        </div>
      </div>
    );
  }

  if (state === 'not_found') {
    return (
      <div className="w-full max-w-md mx-auto">
        <div className="glass p-8 rounded-2xl text-center">
          <div className="w-12 h-12 bg-amber-100 dark:bg-amber-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2">{t('emailNotFound')}</h2>
          <p className="text-slate-600 dark:text-slate-400 mb-6">{t('emailNotFoundDescription')}</p>
          <div className="flex flex-col gap-3">
            <Link href={`/${locale}/register`} className="btn-primary py-2.5 text-center">
              {t('signUp')}
            </Link>
            <button
              type="button"
              onClick={() => setState('idle')}
              className="text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
            >
              {t('tryDifferentEmail')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (state === 'oauth_user') {
    return (
      <div className="w-full max-w-md mx-auto">
        <div className="glass p-8 rounded-2xl text-center">
          <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-blue-600 dark:text-blue-400" viewBox="0 0 24 24" aria-hidden="true">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2">{t('oauthAccountTitle')}</h2>
          <p className="text-slate-600 dark:text-slate-400 mb-6">{t('oauthAccountDescription')}</p>
          <Link href={`/${locale}/login`} className="btn-primary py-2.5 block text-center">
            {t('goToLogin')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="glass p-8 rounded-2xl">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2 text-center">
          {t('forgotPasswordTitle')}
        </h1>
        <p className="text-slate-600 dark:text-slate-400 mb-6 text-center">
          {t('forgotPasswordDescription')}
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t('email')}
            </label>
            <input
              {...register('email')}
              type="email"
              id="email"
              autoComplete="email"
              className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg
                         bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100
                         focus:ring-2 focus:ring-pride-purple focus:border-transparent
                         placeholder:text-slate-400"
              placeholder="you@example.com"
            />
            {errors.email && (
              <p className="mt-1 text-sm text-red-500">{tv(errors.email.message as string)}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary w-full py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? '...' : t('sendResetLink')}
          </button>
        </form>

        <p className="mt-6 text-center text-sm">
          <Link href={`/${locale}/login`} className="text-pride-purple hover:underline font-medium">
            {t('backToLogin')}
          </Link>
        </p>
      </div>
    </div>
  );
}
