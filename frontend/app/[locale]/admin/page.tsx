import { getTranslations, setRequestLocale } from 'next-intl/server';
import AdminDashboard from '@/components/dashboard/AdminDashboard';

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
    refresh: t('admin.refresh'),
    lastUpdated: t('admin.lastUpdated'),
    timeRanges: {
      today: t('admin.timeRanges.today'),
      week: t('admin.timeRanges.week'),
      month: t('admin.timeRanges.month'),
      year: t('admin.timeRanges.year'),
    },
    kpis: {
      totalAnalyses: t('admin.kpi.totalAnalyses'),
      issuesFound: t('admin.kpi.issuesFound'),
      resolved: t('admin.kpi.resolved'),
      avgScore: t('admin.kpi.avgScore'),
      activeUsers: t('admin.kpi.activeUsers'),
      documentsProcessed: t('admin.kpi.documentsProcessed'),
    },
    sections: {
      scoreTrends: t('admin.scoreTrends'),
      scoreTrendsDesc: t('admin.avgOverTime'),
      issuesBreakdown: t('admin.issuesBreakdown'),
      issuesBreakdownDesc: t('admin.shareByCategory'),
      topTerms: t('admin.topTerms'),
      topTermsDesc: t('admin.topTermsDesc'),
      recentActivity: t('admin.recentActivity'),
      recentActivityDesc: t('admin.recentActivityDesc'),
      usageByLanguage: t('admin.usageByLanguage'),
      documentTypes: t('admin.documentTypes'),
      peakHours: t('admin.peakHours'),
      platformHealth: t('admin.platformHealth'),
    },
    table: {
      term: t('admin.table.term'),
      occurrences: t('admin.table.occurrences'),
      suggestion: t('admin.table.suggestion'),
      trend: t('admin.table.trend'),
    },
    activity: {
      analyzed: t('admin.activity.analyzed'),
      found: t('admin.activity.found'),
      issues: t('admin.activity.issues'),
    },
    health: {
      apiLatency: t('admin.health.apiLatency'),
      uptime: t('admin.health.uptime'),
      errorRate: t('admin.health.errorRate'),
      queueSize: t('admin.health.queueSize'),
    },
    languages: {
      en: t('admin.languages.en'),
      he: t('admin.languages.he'),
    },
    since: t('admin.kpi.since'),
    runs: t('admin.runs'),
  };

  return <AdminDashboard translations={translations} />;
}
