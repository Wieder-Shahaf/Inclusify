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
      rules: t('admin.tabs.rules'),
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
        hybrid: t('admin.modelMetrics.modeBreakdown.hybrid'),
        rulesOnly: t('admin.modelMetrics.modeBreakdown.rulesOnly'),
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
    rules: {
      title: t('admin.rules.title'),
      addRule: t('admin.rules.addRule'),
      filters: {
        allLanguages: t('admin.rules.filters.allLanguages'),
        allCategories: t('admin.rules.filters.allCategories'),
        allStatuses: t('admin.rules.filters.allStatuses'),
        active: t('admin.rules.filters.active'),
        inactive: t('admin.rules.filters.inactive'),
      },
      table: {
        name: t('admin.rules.table.name'),
        language: t('admin.rules.table.language'),
        category: t('admin.rules.table.category'),
        severity: t('admin.rules.table.severity'),
        patternType: t('admin.rules.table.patternType'),
        status: t('admin.rules.table.status'),
        actions: t('admin.rules.table.actions'),
      },
      form: {
        addTitle: t('admin.rules.form.addTitle'),
        editTitle: t('admin.rules.form.editTitle'),
        language: t('admin.rules.form.language'),
        name: t('admin.rules.form.name'),
        description: t('admin.rules.form.description'),
        category: t('admin.rules.form.category'),
        severity: t('admin.rules.form.severity'),
        patternType: t('admin.rules.form.patternType'),
        patternValue: t('admin.rules.form.patternValue'),
        exampleBad: t('admin.rules.form.exampleBad'),
        exampleGood: t('admin.rules.form.exampleGood'),
        save: t('admin.rules.form.save'),
        cancel: t('admin.rules.form.cancel'),
        saving: t('admin.rules.form.saving'),
      },
      deleteConfirm: t('admin.rules.deleteConfirm'),
      noRules: t('admin.rules.noRules'),
      severityLabels: {
        low: t('admin.rules.severityLabels.low'),
        medium: t('admin.rules.severityLabels.medium'),
        high: t('admin.rules.severityLabels.high'),
      },
      patternTypeLabels: {
        regex: t('admin.rules.patternTypeLabels.regex'),
        keyword: t('admin.rules.patternTypeLabels.keyword'),
        prompt: t('admin.rules.patternTypeLabels.prompt'),
        other: t('admin.rules.patternTypeLabels.other'),
      },
    },
  };

  return (
    <AdminGuard>
      <AdminDashboard translations={translations} />
    </AdminGuard>
  );
}
