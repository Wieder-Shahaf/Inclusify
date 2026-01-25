'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  TrendingUp,
  TrendingDown,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Target,
  Users,
  Clock,
  Globe,
  Activity,
  BarChart3,
  PieChart,
  RefreshCw,
  Calendar,
  ArrowUpRight,
  Zap,
  Eye,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import SimpleLineChart from './SimpleLineChart';
import DonutChart from './DonutChart';

interface AdminDashboardProps {
  translations: {
    title: string;
    subtitle: string;
    refresh: string;
    lastUpdated: string;
    timeRanges: {
      today: string;
      week: string;
      month: string;
      year: string;
    };
    kpis: {
      totalAnalyses: string;
      issuesFound: string;
      resolved: string;
      avgScore: string;
      activeUsers: string;
      documentsProcessed: string;
    };
    sections: {
      scoreTrends: string;
      scoreTrendsDesc: string;
      issuesBreakdown: string;
      issuesBreakdownDesc: string;
      topTerms: string;
      topTermsDesc: string;
      recentActivity: string;
      recentActivityDesc: string;
      usageByLanguage: string;
      documentTypes: string;
      peakHours: string;
      platformHealth: string;
    };
    table: {
      term: string;
      occurrences: string;
      suggestion: string;
      trend: string;
    };
    activity: {
      analyzed: string;
      found: string;
      issues: string;
    };
    health: {
      apiLatency: string;
      uptime: string;
      errorRate: string;
      queueSize: string;
    };
    languages: {
      en: string;
      he: string;
    };
    since: string;
    runs: string;
  };
}

// Mock real-time data generator
const generateActivityFeed = () => [
  { id: 1, type: 'analysis', user: 'researcher_42', document: 'lgbtq_healthcare_study.pdf', issues: 7, time: '2 min ago' },
  { id: 2, type: 'analysis', user: 'academic_writer', document: 'diversity_report.docx', issues: 3, time: '5 min ago' },
  { id: 3, type: 'analysis', user: 'student_2024', document: 'thesis_chapter_4.pdf', issues: 12, time: '8 min ago' },
  { id: 4, type: 'analysis', user: 'prof_linguistics', document: 'language_evolution.txt', issues: 2, time: '12 min ago' },
  { id: 5, type: 'analysis', user: 'hr_consultant', document: 'policy_update.docx', issues: 5, time: '15 min ago' },
];

// Skeleton loader component
function SkeletonLoader({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <div className={cn('animate-pulse bg-slate-200 dark:bg-slate-700 rounded', className)} style={style} />
  );
}

// Chart container with loading state
function ChartContainer({
  children,
  isLoading,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  isLoading: boolean;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30, scale: 0.95 }}
      animate={isLoading ? { opacity: 0, y: 30, scale: 0.95 } : { opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.5,
        delay: isLoading ? 0 : delay,
        ease: [0.25, 0.46, 0.45, 0.94]
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export default function AdminDashboard({ translations }: AdminDashboardProps) {
  const [timeRange, setTimeRange] = useState<'today' | 'week' | 'month' | 'year'>('month');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [activityFeed, setActivityFeed] = useState(generateActivityFeed());
  const [isLoading, setIsLoading] = useState(true);

  // Simulate initial data loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 800);
    return () => clearTimeout(timer);
  }, []);

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdated(new Date());
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setActivityFeed(generateActivityFeed());
      setLastUpdated(new Date());
      setIsRefreshing(false);
    }, 1000);
  };

  // KPI Data based on time range
  const kpiData = {
    today: { analyses: 47, issues: 312, resolved: 289, score: 84, users: 23, docs: 52 },
    week: { analyses: 247, issues: 1829, resolved: 1654, score: 82, users: 89, docs: 284 },
    month: { analyses: 1247, issues: 8293, resolved: 7841, score: 81, users: 342, docs: 1456 },
    year: { analyses: 12847, issues: 89234, resolved: 84521, score: 79, users: 2847, docs: 15234 },
  }[timeRange];

  const kpiChanges = {
    today: { analyses: 15, issues: -8, resolved: 12, score: 3, users: 8, docs: 11 },
    week: { analyses: 12, issues: -5, resolved: 15, score: 5, users: 14, docs: 18 },
    month: { analyses: 23, issues: -12, resolved: 28, score: 8, users: 32, docs: 25 },
    year: { analyses: 45, issues: -18, resolved: 52, score: 12, users: 67, docs: 58 },
  }[timeRange];

  const trendData = {
    today: [78, 80, 82, 79, 84, 83, 85, 84, 86, 84, 85, 84],
    week: [72, 74, 76, 78, 80, 79, 82],
    month: [68, 70, 69, 73, 76, 80, 77, 82, 81, 85, 84, 82],
    year: [62, 65, 68, 70, 72, 75, 78, 80, 79, 82, 81, 81],
  }[timeRange];

  const trendLabels = {
    today: ['6am', '8am', '10am', '12pm', '2pm', '4pm', '6pm', '8pm', '10pm', '12am', '2am', '4am'],
    week: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    month: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    year: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  }[timeRange];

  const issuesData = [
    { label: 'Outdated', value: 45, color: '#3b82f6' },
    { label: 'Biased', value: 30, color: '#f59e0b' },
    { label: 'Offensive', value: 15, color: '#ef4444' },
    { label: 'Incorrect', value: 10, color: '#8b5cf6' },
  ];

  const documentTypes = [
    { type: 'PDF', count: 156, percentage: 62, color: '#ef4444' },
    { type: 'DOCX', count: 67, percentage: 27, color: '#3b82f6' },
    { type: 'TXT', count: 18, percentage: 7, color: '#6b7280' },
    { type: 'PPTX', count: 6, percentage: 4, color: '#f59e0b' },
  ];

  const peakHours = [
    { hour: '9am', value: 85 },
    { hour: '10am', value: 92 },
    { hour: '11am', value: 78 },
    { hour: '12pm', value: 45 },
    { hour: '1pm', value: 52 },
    { hour: '2pm', value: 88 },
    { hour: '3pm', value: 95 },
    { hour: '4pm', value: 72 },
    { hour: '5pm', value: 58 },
  ];

  const topTerms = [
    { term: 'homosexual', count: 123, suggestion: 'gay/lesbian', trend: 12 },
    { term: 'sexual preference', count: 94, suggestion: 'sexual orientation', trend: -5 },
    { term: 'transsexual', count: 71, suggestion: 'transgender person', trend: 8 },
    { term: 'born as a man', count: 38, suggestion: 'assigned male at birth', trend: -15 },
    { term: 'normal people', count: 29, suggestion: 'cisgender/heterosexual', trend: 3 },
  ];

  const languages = [
    { lang: translations.languages.en, runs: 142, percentage: 60 },
    { lang: translations.languages.he, runs: 95, percentage: 40 },
  ];

  const healthMetrics = [
    { label: translations.health.apiLatency, value: '45ms', status: 'good' },
    { label: translations.health.uptime, value: '99.9%', status: 'good' },
    { label: translations.health.errorRate, value: '0.1%', status: 'good' },
    { label: translations.health.queueSize, value: '3', status: 'good' },
  ];

  const timeRangeOptions = [
    { key: 'today', label: translations.timeRanges.today },
    { key: 'week', label: translations.timeRanges.week },
    { key: 'month', label: translations.timeRanges.month },
    { key: 'year', label: translations.timeRanges.year },
  ];

  return (
    <div className="py-4 px-2 space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-pride-purple" />
            {translations.title}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {translations.subtitle}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Time Range Selector */}
          <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-100 dark:bg-slate-800">
            {timeRangeOptions.map((option) => (
              <button
                key={option.key}
                onClick={() => setTimeRange(option.key as typeof timeRange)}
                className={cn(
                  'px-3 py-1.5 rounded-md text-sm font-medium transition-all',
                  timeRange === option.key
                    ? 'bg-white dark:bg-slate-700 text-pride-purple shadow-sm'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                )}
              >
                {option.label}
              </button>
            ))}
          </div>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-pride-purple/10 text-pride-purple hover:bg-pride-purple/20 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={cn('w-4 h-4', isRefreshing && 'animate-spin')} />
            <span className="text-sm font-medium hidden sm:inline">{translations.refresh}</span>
          </button>
        </div>
      </div>

      {/* Last Updated */}
      <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
        <Clock className="w-3 h-3" />
        <span>{translations.lastUpdated}: {lastUpdated.toLocaleTimeString()}</span>
        <span className="flex items-center gap-1 text-green-500">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
          Live
        </span>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <KpiCard
          label={translations.kpis.totalAnalyses}
          value={kpiData.analyses.toLocaleString()}
          change={kpiChanges.analyses}
          icon={<FileText className="w-5 h-5" />}
          color="sky"
          isLoading={isLoading}
          delay={0}
        />
        <KpiCard
          label={translations.kpis.issuesFound}
          value={kpiData.issues.toLocaleString()}
          change={kpiChanges.issues}
          icon={<AlertTriangle className="w-5 h-5" />}
          color="amber"
          invertChange
          isLoading={isLoading}
          delay={0.05}
        />
        <KpiCard
          label={translations.kpis.resolved}
          value={kpiData.resolved.toLocaleString()}
          change={kpiChanges.resolved}
          icon={<CheckCircle2 className="w-5 h-5" />}
          color="green"
          isLoading={isLoading}
          delay={0.1}
        />
        <KpiCard
          label={translations.kpis.avgScore}
          value={`${kpiData.score}%`}
          change={kpiChanges.score}
          icon={<Target className="w-5 h-5" />}
          color="purple"
          isLoading={isLoading}
          delay={0.15}
        />
        <KpiCard
          label={translations.kpis.activeUsers}
          value={kpiData.users.toLocaleString()}
          change={kpiChanges.users}
          icon={<Users className="w-5 h-5" />}
          color="pink"
          isLoading={isLoading}
          delay={0.2}
        />
        <KpiCard
          label={translations.kpis.documentsProcessed}
          value={kpiData.docs.toLocaleString()}
          change={kpiChanges.docs}
          icon={<Eye className="w-5 h-5" />}
          color="indigo"
          isLoading={isLoading}
          delay={0.25}
        />
      </div>

      {/* Main Charts Row */}
      <div className="grid gap-4 xl:grid-cols-3">
        {/* Score Trends - Takes 2 columns */}
        <ChartContainer isLoading={isLoading} delay={0.3} className="xl:col-span-2 rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
          {isLoading ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <SkeletonLoader className="h-5 w-32 mb-2" />
                  <SkeletonLoader className="h-3 w-48" />
                </div>
                <SkeletonLoader className="h-8 w-20 rounded-lg" />
              </div>
              <SkeletonLoader className="h-[200px] w-full rounded-xl" />
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2">
                    <Activity className="w-4 h-4 text-pride-purple" />
                    {translations.sections.scoreTrends}
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {translations.sections.scoreTrendsDesc}
                  </p>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-green-50 dark:bg-green-900/20">
                  <TrendingUp className="w-4 h-4 text-green-500" />
                  <span className="text-sm font-medium text-green-600 dark:text-green-400">+{kpiChanges.score}%</span>
                </div>
              </div>
              <div className="h-[200px]">
                <SimpleLineChart data={trendData} labels={trendLabels} color="#7b61ff" height={200} />
              </div>
            </>
          )}
        </ChartContainer>

        {/* Issues Breakdown */}
        <ChartContainer isLoading={isLoading} delay={0.4} className="rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
          {isLoading ? (
            <div className="space-y-4">
              <SkeletonLoader className="h-5 w-36 mb-1" />
              <SkeletonLoader className="h-3 w-28" />
              <div className="flex items-center justify-center gap-4 mt-4">
                <SkeletonLoader className="h-[140px] w-[140px] rounded-full" />
                <div className="space-y-2">
                  {[1, 2, 3, 4].map((i) => (
                    <SkeletonLoader key={i} className="h-4 w-24" />
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2 mb-1">
                <PieChart className="w-4 h-4 text-pride-purple" />
                {translations.sections.issuesBreakdown}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
                {translations.sections.issuesBreakdownDesc}
              </p>
              <div className="flex items-center justify-center gap-4">
                <DonutChart
                  data={issuesData}
                  size={140}
                  thickness={16}
                  center={{
                    title: kpiData.issues.toLocaleString(),
                    subtitle: 'Total',
                    titleClassName: 'text-lg font-bold',
                    subtitleClassName: 'text-[10px] text-slate-500',
                  }}
                />
                <div className="space-y-2">
                  {issuesData.map((d, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: 10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.5 + i * 0.05 }}
                      className="flex items-center gap-2"
                    >
                      <span className="w-3 h-3 rounded-full" style={{ backgroundColor: d.color }} />
                      <span className="text-xs text-slate-600 dark:text-slate-400">{d.label}</span>
                      <span className="text-xs font-semibold text-slate-800 dark:text-white">{d.value}%</span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </>
          )}
        </ChartContainer>
      </div>

      {/* Secondary Row */}
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        {/* Recent Activity */}
        <ChartContainer isLoading={isLoading} delay={0.5} className="xl:col-span-2 rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
          {isLoading ? (
            <div className="space-y-4">
              <SkeletonLoader className="h-5 w-32 mb-1" />
              <SkeletonLoader className="h-3 w-40" />
              <div className="space-y-3">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50">
                    <SkeletonLoader className="w-8 h-8 rounded-lg" />
                    <div className="flex-1">
                      <SkeletonLoader className="h-4 w-40 mb-2" />
                      <SkeletonLoader className="h-3 w-24" />
                    </div>
                    <SkeletonLoader className="h-3 w-16" />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2 mb-1">
                <Zap className="w-4 h-4 text-pride-purple" />
                {translations.sections.recentActivity}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
                {translations.sections.recentActivityDesc}
              </p>
              <div className="space-y-3 max-h-[200px] overflow-y-auto">
                <AnimatePresence>
                  {activityFeed.map((activity, idx) => (
                    <motion.div
                      key={activity.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      transition={{ delay: 0.6 + idx * 0.08 }}
                      className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50"
                    >
                      <div className="w-8 h-8 rounded-lg bg-pride-purple/10 flex items-center justify-center">
                        <FileText className="w-4 h-4 text-pride-purple" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800 dark:text-white truncate">
                          {activity.document}
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {translations.activity.found} <span className="font-semibold text-amber-600">{activity.issues}</span> {translations.activity.issues}
                        </p>
                      </div>
                      <div className="text-xs text-slate-400">{activity.time}</div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </>
          )}
        </ChartContainer>

        {/* Document Types */}
        <ChartContainer isLoading={isLoading} delay={0.6} className="rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
          {isLoading ? (
            <div className="space-y-4">
              <SkeletonLoader className="h-5 w-32" />
              <div className="space-y-3 mt-4">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i}>
                    <div className="flex justify-between mb-1">
                      <SkeletonLoader className="h-4 w-12" />
                      <SkeletonLoader className="h-4 w-16" />
                    </div>
                    <SkeletonLoader className="h-2 w-full rounded-full" />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2 mb-4">
                <FileText className="w-4 h-4 text-pride-purple" />
                {translations.sections.documentTypes}
              </h3>
              <div className="space-y-3">
                {documentTypes.map((doc, i) => (
                  <div key={i}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="font-medium text-slate-700 dark:text-slate-300">{doc.type}</span>
                      <span className="text-slate-500 dark:text-slate-400">{doc.count} ({doc.percentage}%)</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${doc.percentage}%` }}
                        transition={{ duration: 0.6, delay: 0.7 + i * 0.1, ease: [0.25, 0.46, 0.45, 0.94] }}
                        className="h-full rounded-full"
                        style={{ backgroundColor: doc.color }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </ChartContainer>

        {/* Peak Hours */}
        <ChartContainer isLoading={isLoading} delay={0.7} className="rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
          {isLoading ? (
            <div className="space-y-4">
              <SkeletonLoader className="h-5 w-28" />
              <div className="flex items-end justify-between h-[140px] gap-1 mt-4">
                {[65, 80, 45, 70, 55, 90, 75, 40, 60].map((height, i) => (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1">
                    <SkeletonLoader className="w-full rounded-t-sm" style={{ height: `${height}%` }} />
                    <SkeletonLoader className="h-2 w-6" />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2 mb-4">
                <Clock className="w-4 h-4 text-pride-purple" />
                {translations.sections.peakHours}
              </h3>
              <div className="flex items-end justify-between h-[140px] gap-1">
                {peakHours.map((hour, i) => (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1">
                    <motion.div
                      initial={{ height: 0 }}
                      animate={{ height: `${hour.value}%` }}
                      transition={{ duration: 0.6, delay: 0.8 + i * 0.05, ease: [0.25, 0.46, 0.45, 0.94] }}
                      className={cn(
                        'w-full rounded-t-sm',
                        hour.value > 80 ? 'bg-pride-purple' : hour.value > 50 ? 'bg-pride-purple/60' : 'bg-pride-purple/30'
                      )}
                    />
                    <span className="text-[9px] text-slate-500">{hour.hour}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </ChartContainer>
      </div>

      {/* Bottom Row */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Top Terms */}
        <ChartContainer isLoading={isLoading} delay={0.8} className="lg:col-span-2 rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
          {isLoading ? (
            <div className="space-y-4">
              <SkeletonLoader className="h-5 w-40 mb-1" />
              <SkeletonLoader className="h-3 w-64" />
              <div className="space-y-3 mt-4">
                <div className="flex gap-4 border-b border-slate-100 dark:border-slate-800 pb-2">
                  {[1, 2, 3, 4].map((i) => (
                    <SkeletonLoader key={i} className="h-4 w-20" />
                  ))}
                </div>
                {[1, 2, 3, 4, 5].map((i) => (
                  <div key={i} className="flex gap-4 py-2">
                    <SkeletonLoader className="h-4 w-28" />
                    <SkeletonLoader className="h-4 w-12" />
                    <SkeletonLoader className="h-4 w-32" />
                    <SkeletonLoader className="h-4 w-16 rounded-full" />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2 mb-1">
                <AlertTriangle className="w-4 h-4 text-pride-purple" />
                {translations.sections.topTerms}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
                {translations.sections.topTermsDesc}
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800">
                      <th className="py-2 pr-4 font-medium">{translations.table.term}</th>
                      <th className="py-2 pr-4 font-medium">{translations.table.occurrences}</th>
                      <th className="py-2 pr-4 font-medium">{translations.table.suggestion}</th>
                      <th className="py-2 font-medium">{translations.table.trend}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topTerms.map((row, i) => (
                      <motion.tr
                        key={i}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.9 + i * 0.08, ease: [0.25, 0.46, 0.45, 0.94] }}
                        className="border-b border-slate-50 dark:border-slate-800/50 last:border-0"
                      >
                        <td className="py-3 pr-4">
                          <span className="font-medium text-slate-800 dark:text-white">&ldquo;{row.term}&rdquo;</span>
                        </td>
                        <td className="py-3 pr-4 text-slate-600 dark:text-slate-400">{row.count}</td>
                        <td className="py-3 pr-4">
                          <span className="text-pride-purple font-medium">{row.suggestion}</span>
                        </td>
                        <td className="py-3">
                          <span className={cn(
                            'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                            row.trend > 0
                              ? 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400'
                              : 'bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400'
                          )}>
                            {row.trend > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                            {row.trend > 0 ? '+' : ''}{row.trend}%
                          </span>
                        </td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </ChartContainer>

        {/* Right Column */}
        <div className="space-y-4">
          {/* Language Usage */}
          <ChartContainer isLoading={isLoading} delay={0.9} className="rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
            {isLoading ? (
              <div className="space-y-4">
                <SkeletonLoader className="h-5 w-36" />
                <div className="space-y-4 mt-4">
                  {[1, 2].map((i) => (
                    <div key={i}>
                      <div className="flex justify-between mb-2">
                        <SkeletonLoader className="h-4 w-16" />
                        <SkeletonLoader className="h-4 w-20" />
                      </div>
                      <SkeletonLoader className="h-3 w-full rounded-full" />
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <>
                <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2 mb-4">
                  <Globe className="w-4 h-4 text-pride-purple" />
                  {translations.sections.usageByLanguage}
                </h3>
                <div className="space-y-4">
                  {languages.map((l, i) => (
                    <div key={i}>
                      <div className="flex items-center justify-between text-sm mb-2">
                        <span className="font-medium text-slate-700 dark:text-slate-300">{l.lang}</span>
                        <span className="text-slate-500 dark:text-slate-400">{l.runs} {translations.runs}</span>
                      </div>
                      <div className="h-3 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${l.percentage}%` }}
                          transition={{ duration: 0.6, delay: 1.0 + i * 0.15, ease: [0.25, 0.46, 0.45, 0.94] }}
                          className="h-full rounded-full bg-gradient-to-r from-pride-purple to-pride-pink"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </ChartContainer>

          {/* Platform Health */}
          <ChartContainer isLoading={isLoading} delay={1.0} className="rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
            {isLoading ? (
              <div className="space-y-4">
                <SkeletonLoader className="h-5 w-32" />
                <div className="grid grid-cols-2 gap-3 mt-4">
                  {[1, 2, 3, 4].map((i) => (
                    <div key={i} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50">
                      <SkeletonLoader className="h-2 w-16 mb-2" />
                      <SkeletonLoader className="h-6 w-12" />
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <>
                <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2 mb-4">
                  <Activity className="w-4 h-4 text-pride-purple" />
                  {translations.sections.platformHealth}
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  {healthMetrics.map((metric, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 1.1 + i * 0.08, ease: [0.25, 0.46, 0.45, 0.94] }}
                      className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50"
                    >
                      <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-wide">{metric.label}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-lg font-bold text-slate-800 dark:text-white">{metric.value}</span>
                        <motion.span
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ delay: 1.2 + i * 0.08, type: 'spring', stiffness: 500 }}
                          className="w-2 h-2 rounded-full bg-green-500"
                        />
                      </div>
                    </motion.div>
                  ))}
                </div>
              </>
            )}
          </ChartContainer>
        </div>
      </div>
    </div>
  );
}

// Enhanced KPI Card Component
function KpiCard({
  label,
  value,
  change,
  icon,
  color,
  invertChange = false,
  isLoading = false,
  delay = 0,
}: {
  label: string;
  value: string;
  change: number;
  icon: React.ReactNode;
  color: 'sky' | 'amber' | 'green' | 'purple' | 'pink' | 'indigo';
  invertChange?: boolean;
  isLoading?: boolean;
  delay?: number;
}) {
  const isPositive = invertChange ? change < 0 : change > 0;
  const colorConfig = {
    sky: 'from-sky-500 to-blue-500 bg-sky-50 dark:bg-sky-900/20',
    amber: 'from-amber-500 to-orange-500 bg-amber-50 dark:bg-amber-900/20',
    green: 'from-green-500 to-emerald-500 bg-green-50 dark:bg-green-900/20',
    purple: 'from-purple-500 to-violet-500 bg-purple-50 dark:bg-purple-900/20',
    pink: 'from-pink-500 to-rose-500 bg-pink-50 dark:bg-pink-900/20',
    indigo: 'from-indigo-500 to-blue-500 bg-indigo-50 dark:bg-indigo-900/20',
  }[color];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9, y: 20 }}
      animate={isLoading ? { opacity: 0, scale: 0.9, y: 20 } : { opacity: 1, scale: 1, y: 0 }}
      transition={{
        duration: 0.4,
        delay: isLoading ? 0 : delay,
        ease: [0.25, 0.46, 0.45, 0.94]
      }}
      whileHover={{ y: -2, transition: { duration: 0.2 } }}
      className="rounded-xl border bg-white dark:bg-slate-900 p-4 shadow-sm"
    >
      {isLoading ? (
        <div className="space-y-3">
          <div className="flex items-start justify-between">
            <SkeletonLoader className="w-10 h-10 rounded-xl" />
            <SkeletonLoader className="w-14 h-6 rounded-full" />
          </div>
          <div>
            <SkeletonLoader className="h-8 w-20 mb-2" />
            <SkeletonLoader className="h-3 w-24" />
          </div>
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between">
            <div className={cn('w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center text-white', colorConfig.split(' ')[0], colorConfig.split(' ')[1])}>
              {icon}
            </div>
            <motion.div
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: delay + 0.2, type: 'spring', stiffness: 500 }}
              className={cn(
                'flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                isPositive
                  ? 'bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400'
                  : 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400'
              )}
            >
              {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              {change > 0 ? '+' : ''}{change}%
            </motion.div>
          </div>
          <div className="mt-3">
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: delay + 0.1 }}
              className="text-2xl font-bold text-slate-800 dark:text-white"
            >
              {value}
            </motion.p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{label}</p>
          </div>
        </>
      )}
    </motion.div>
  );
}
