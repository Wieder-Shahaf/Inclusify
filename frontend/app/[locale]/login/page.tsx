import { Suspense } from 'react';
import { setRequestLocale } from 'next-intl/server';
import { LoginForm } from '@/components/auth/LoginForm';

type Props = {
  params: Promise<{ locale: string }>;
};

function LoginFormSkeleton() {
  return (
    <div className="w-full max-w-md mx-auto">
      <div className="glass p-8 rounded-2xl animate-pulse">
        <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-24 mx-auto mb-6" />
        <div className="h-10 bg-slate-200 dark:bg-slate-700 rounded mb-6" />
        <div className="h-px bg-slate-200 dark:bg-slate-700 my-6" />
        <div className="space-y-4">
          <div className="h-10 bg-slate-200 dark:bg-slate-700 rounded" />
          <div className="h-10 bg-slate-200 dark:bg-slate-700 rounded" />
          <div className="h-10 bg-slate-200 dark:bg-slate-700 rounded" />
        </div>
      </div>
    </div>
  );
}

export default async function LoginPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <div className="flex-1 flex items-center justify-center py-12">
      <Suspense fallback={<LoginFormSkeleton />}>
        <LoginForm locale={locale} />
      </Suspense>
    </div>
  );
}
