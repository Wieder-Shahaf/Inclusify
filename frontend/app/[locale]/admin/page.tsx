import { getTranslations, setRequestLocale } from 'next-intl/server';
import AdminDashboard from '@/components/dashboard/AdminDashboard';
import { AdminGuard } from '@/components/auth/AuthGuard';

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function AdminPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  const t = await getTranslations();

  const translations = {
    title: t('admin.title'),
    subtitle: t('admin.subtitle'),
    tabs: {
      overview: t('admin.tabs.overview'),
      users: t('admin.tabs.users'),
    },
    timeRanges: {
      week: t('admin.timeRanges.week'),
      month: t('admin.timeRanges.month'),
      quarter: t('admin.timeRanges.quarter'),
      year: t('admin.timeRanges.year'),
    },
    kpis: {
      totalAnalyses: t('admin.kpi.totalAnalyses'),
      activeUsers: t('admin.kpi.activeUsers'),
      documentsProcessed: t('admin.kpi.documentsProcessed'),
    },
    sections: {
      recentActivity: t('admin.recentActivity'),
      recentActivityDesc: t('admin.recentActivityDesc'),
    },
    activity: {
      found: t('admin.activity.found'),
      issues: t('admin.activity.issues'),
    },
    users: {
      searchPlaceholder: t('admin.users.searchPlaceholder'),
      noResults: t('admin.users.noResults'),
    },
  };

  return (
    <AdminGuard>
      <AdminDashboard translations={translations} />
    </AdminGuard>
  );
}
