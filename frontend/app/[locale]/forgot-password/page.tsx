import { Suspense } from 'react';
import { setRequestLocale } from 'next-intl/server';
import { ForgotPasswordForm } from '@/components/auth/ForgotPasswordForm';

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function ForgotPasswordPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <div className="flex-1 flex items-center justify-center py-12">
      <Suspense>
        <ForgotPasswordForm locale={locale} />
      </Suspense>
    </div>
  );
}
