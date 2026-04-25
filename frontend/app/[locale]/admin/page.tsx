import { getTranslations, setRequestLocale } from 'next-intl/server';
import { AdminGuard } from '@/components/auth/AuthGuard';
import dynamic from 'next/dynamic';

const AdminDashboard = dynamic(() => import('@/components/dashboard/AdminDashboard'));

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
      modelPerformance: t('admin.tabs.modelPerformance'),
      feedback: t('admin.tabs.feedback'),
    },
    modelMetrics: {
      kpis: {
        avgLatency: t('admin.modelMetrics.kpis.avgLatency'),
        errorRate: t('admin.modelMetrics.kpis.errorRate'),
        fallbackRate: t('admin.modelMetrics.kpis.fallbackRate'),
        totalLlmCalls: t('admin.modelMetrics.kpis.totalLlmCalls'),
      },
      modeBreakdown: {
        title: t('admin.modelMetrics.modeBreakdown.title'),
        llm: t('admin.modelMetrics.modeBreakdown.llm'),
        analyses: t('admin.modelMetrics.modeBreakdown.analyses'),
      },
      noData: t('admin.modelMetrics.noData'),
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
      totalUsers: t('admin.kpi.totalUsers'),
      findingsFound: t('admin.kpi.issuesFound'),
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
    feedback: {
      title: t('admin.feedback.title'),
      filterAll: t('admin.feedback.filterAll'),
      filterUp: t('admin.feedback.filterUp'),
      filterDown: t('admin.feedback.filterDown'),
      colVote: t('admin.feedback.colVote'),
      colFlaggedText: t('admin.feedback.colFlaggedText'),
      colSeverity: t('admin.feedback.colSeverity'),
      colUser: t('admin.feedback.colUser'),
      colDate: t('admin.feedback.colDate'),
      colComment: t('admin.feedback.colComment'),
      noData: t('admin.feedback.noData'),
      helpful: t('admin.feedback.helpful'),
      falsePositive: t('admin.feedback.falsePositive'),
      anonymous: t('admin.feedback.anonymous'),
    },
  };

  return (
    <AdminGuard>
      <AdminDashboard translations={translations} />
    </AdminGuard>
  );
}
