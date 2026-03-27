'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useTranslations } from 'next-intl';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { toast } from 'sonner';
import { resetPassword } from '@/lib/api/auth';

const resetPasswordSchema = z.object({
  password: z.string().min(8, 'passwordMin'),
  confirmPassword: z.string().min(1, 'passwordRequired'),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'passwordMatch',
  path: ['confirmPassword'],
});

type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

export function ResetPasswordForm({ locale }: { locale: string }) {
  const t = useTranslations('auth');
  const tv = useTranslations('auth.validation');
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
  });

  if (!token) {
    return (
      <div className="w-full max-w-md mx-auto">
        <div className="glass p-8 rounded-2xl text-center">
          <div className="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            {t('invalidResetToken')}
          </h2>
          <Link
            href={`/${locale}/forgot-password`}
            className="text-pride-purple hover:underline font-medium"
          >
            {t('sendResetLink')}
          </Link>
        </div>
      </div>
    );
  }

  const onSubmit = async (data: ResetPasswordFormData) => {
    setIsSubmitting(true);
    try {
      await resetPassword(token, data.password);
      toast.success(t('resetPasswordSuccess'));
      router.push(`/${locale}/login`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t('errors.generic'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="glass p-8 rounded-2xl">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-6 text-center">
          {t('resetPasswordTitle')}
        </h1>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t('newPassword')}
            </label>
            <input
              {...register('password')}
              type="password"
              id="password"
              autoComplete="new-password"
              className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg
                         bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100
                         focus:ring-2 focus:ring-pride-purple focus:border-transparent"
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-500">{tv(errors.password.message as string)}</p>
            )}
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              {t('confirmNewPassword')}
            </label>
            <input
              {...register('confirmPassword')}
              type="password"
              id="confirmPassword"
              autoComplete="new-password"
              className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg
                         bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100
                         focus:ring-2 focus:ring-pride-purple focus:border-transparent"
            />
            {errors.confirmPassword && (
              <p className="mt-1 text-sm text-red-500">{tv(errors.confirmPassword.message as string)}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary w-full py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? '...' : t('resetPassword')}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
          <Link href={`/${locale}/login`} className="text-pride-purple hover:underline font-medium">
            {t('backToLogin')}
          </Link>
        </p>
      </div>
    </div>
  );
}
