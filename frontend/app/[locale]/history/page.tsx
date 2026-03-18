import { setRequestLocale, getTranslations } from 'next-intl/server';
import { History } from 'lucide-react';

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function HistoryPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations('app');

  return (
    <div className="flex-1 flex items-center justify-center py-12">
      <div className="text-center max-w-md mx-auto px-4">
        <div className="mb-6 flex justify-center">
          <div className="p-4 bg-slate-100 dark:bg-slate-800 rounded-full">
            <History className="w-12 h-12 text-slate-400 dark:text-slate-500" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-3">
          {t('myAnalyses') || 'My Analyses'}
        </h1>
        <p className="text-slate-600 dark:text-slate-400 mb-6">
          {locale === 'he'
            ? 'היסטוריית הניתוחים שלך תהיה זמינה בקרוב. אנחנו עובדים על זה!'
            : 'Your analysis history will be available soon. We\'re working on it!'}
        </p>
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-pride-purple/10 text-pride-purple rounded-lg text-sm font-medium">
          {locale === 'he' ? 'בקרוב' : 'Coming Soon'}
        </div>
      </div>
    </div>
  );
}
