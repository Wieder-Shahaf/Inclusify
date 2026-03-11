import { setRequestLocale } from 'next-intl/server';
import { RegisterForm } from '@/components/auth/RegisterForm';

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function RegisterPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  return (
    <div className="flex-1 flex items-center justify-center py-12">
      <RegisterForm locale={locale} />
    </div>
  );
}
