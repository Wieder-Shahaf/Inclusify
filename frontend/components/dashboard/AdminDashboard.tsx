'use client';

import { useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';
import ModelPerformanceTab from './ModelPerformanceTab';
import OverviewTab from './OverviewTab';
import UsersTab from './UsersTab';
import FeedbackTab from './FeedbackTab';

interface AdminDashboardProps {
  translations: {
    title: string;
    subtitle: string;
    tabs: {
      overview: string;
      users: string;
      modelPerformance: string;
      feedback: string;
    };
    modelMetrics: {
      kpis: {
        avgLatency: string;
        errorRate: string;
        fallbackRate: string;
        totalLlmCalls: string;
      };
      modeBreakdown: {
        title: string;
        llm: string;
        analyses: string;
      };
      noData: string;
    };
    timeRanges: {
      week: string;
      month: string;
      quarter: string;
      year: string;
    };
    kpis: {
      totalAnalyses: string;
      activeUsers: string;
      totalUsers: string;
      findingsFound: string;
    };
    sections: {
      recentActivity: string;
      recentActivityDesc: string;
    };
    activity: {
      found: string;
      issues: string;
    };
    users: {
      searchPlaceholder: string;
      noResults: string;
    };
    feedback: {
      title: string;
      filterAll: string;
      filterUp: string;
      filterDown: string;
      colVote: string;
      colFlaggedText: string;
      colSeverity: string;
      colUser: string;
      colDate: string;
      colComment: string;
      noData: string;
      helpful: string;
      falsePositive: string;
      anonymous: string;
    };
  };
}

type TabKey = 'overview' | 'users' | 'model-performance' | 'feedback';

// Skeleton loader for suspense fallback
function DashboardSkeleton() {
  return (
    <div className="mx-auto flex w-full flex-1 min-h-0 flex-col gap-3 py-3 animate-pulse lg:w-[calc(100%-10.5rem)]">
      <div className="flex shrink-0 items-center justify-between">
        <div>
          <div className="h-7 w-48 bg-slate-200 dark:bg-slate-700 rounded mb-2" />
          <div className="h-4 w-64 bg-slate-200 dark:bg-slate-700 rounded" />
        </div>
        <div className="h-10 w-32 bg-slate-200 dark:bg-slate-700 rounded" />
      </div>
      <div className="h-11 w-full bg-slate-200 dark:bg-slate-700 rounded" />
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-16 bg-slate-200 dark:bg-slate-700 rounded-xl" />
        ))}
      </div>
    </div>
  );
}

function AdminDashboardContent({ translations }: AdminDashboardProps) {
  const searchParams = useSearchParams();
  const router = useRouter();

  const activeTab = (searchParams.get('tab') as TabKey) || 'overview';
  const [days, setDays] = useState<number>(30);

  const setActiveTab = (tab: TabKey) => {
    const params = new URLSearchParams(searchParams);
    params.set('tab', tab);
    router.push(`?${params.toString()}`);
  };

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'overview', label: translations.tabs.overview },
    { key: 'users', label: translations.tabs.users },
    { key: 'model-performance', label: translations.tabs.modelPerformance },
    { key: 'feedback', label: translations.tabs.feedback },
  ];

  const timeRangeOptions = [
    { value: 7, label: translations.timeRanges.week },
    { value: 30, label: translations.timeRanges.month },
    { value: 90, label: translations.timeRanges.quarter },
    { value: 365, label: translations.timeRanges.year },
  ];

  return (
    // Centered with mx-auto, NOT `relative left-1/2 -translate-x-1/2`: that hack
    // assumes the box starts at the parent's left edge, which is only true in LTR.
    // <main> is a column flex container, so in RTL (he) the cross-axis start flips
    // to the right, the box got shoved off-center, and main's overflow-x-hidden
    // clipped the overhang. mx-auto absorbs free space in either direction.
    <div className="mx-auto flex w-full flex-col gap-3 py-3 lg:min-h-0 lg:flex-1 lg:overflow-hidden lg:w-[calc(100%-10.5rem)]">
      {/* Header with time range selector */}
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-pride-purple" />
            {translations.title}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {translations.subtitle}
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-3 py-2 rounded-lg border bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple/50"
        >
          {timeRangeOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Tab Navigation — scrolls horizontally on mobile (labels show in full,
          no truncation); even 4-column grid on desktop. */}
      <div className="flex h-11 shrink-0 overflow-x-auto border-b border-slate-200 dark:border-slate-700 lg:grid lg:grid-cols-4">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'h-11 shrink-0 whitespace-nowrap px-4 text-center text-sm font-medium border-b-2 -mb-px transition-colors lg:px-2',
              activeTab === tab.key
                ? 'border-pride-purple text-pride-purple'
                : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="lg:min-h-0 lg:flex-1 lg:overflow-hidden">
        {activeTab === 'overview' && (
          <OverviewTab
            days={days}
            translations={{
              kpis: translations.kpis,
              sections: translations.sections,
              activity: translations.activity,
            }}
          />
        )}
        {activeTab === 'users' && (
          <UsersTab translations={{ users: translations.users }} />
        )}
        {activeTab === 'model-performance' && (
          <ModelPerformanceTab
            days={days}
            translations={translations.modelMetrics}
          />
        )}
        {activeTab === 'feedback' && (
          <FeedbackTab translations={translations.feedback} />
        )}
      </div>
    </div>
  );
}

// Wrap with Suspense for useSearchParams (required in Next.js 14+)
export default function AdminDashboard({ translations }: AdminDashboardProps) {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <AdminDashboardContent translations={translations} />
    </Suspense>
  );
}
