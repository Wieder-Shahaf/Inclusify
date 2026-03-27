'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useTranslations } from 'next-intl';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { GoogleSignInButton } from './GoogleSignInButton';

const loginSchema = z.object({
  email: z.string().min(1, 'emailRequired').email('emailInvalid'),
  password: z.string().min(1, 'passwordRequired'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export function LoginForm({ locale }: { locale: string }) {
  const t = useTranslations('auth');
  const tv = useTranslations('auth.validation');
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setIsSubmitting(true);
    try {
      await login(data.email, data.password);
      toast.success(t('loginSuccess'));

      const returnUrl = searchParams.get('returnUrl') || `/${locale}`;
      router.push(returnUrl);
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
          {t('login')}
        </h1>

        <GoogleSignInButton />

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200 dark:border-slate-700" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-4 bg-white dark:bg-slate-900 text-slate-500">
              {t('orContinueWith')}
            </span>
          </div>
        </div>

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

          <div>
            <div className="flex items-center justify-between mb-1">
              <label htmlFor="password" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                {t('password')}
              </label>
              <Link href={`/${locale}/forgot-password`} className="text-sm text-pride-purple hover:underline">
                {t('forgotPassword')}
              </Link>
            </div>
            <input
              {...register('password')}
              type="password"
              id="password"
              autoComplete="current-password"
              className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg
                         bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100
                         focus:ring-2 focus:ring-pride-purple focus:border-transparent"
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-500">{tv(errors.password.message as string)}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary w-full py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? t('loggingIn') : t('signIn')}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
          {t('noAccount')}{' '}
          <Link href={`/${locale}/register`} className="text-pride-purple hover:underline font-medium">
            {t('signUp')}
          </Link>
        </p>
      </div>
    </div>
  );
}
