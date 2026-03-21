'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Users,
  FileText,
  Activity,
  BarChart3,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAdminKPIs, useAdminActivity } from '@/lib/api/admin';

interface OverviewTabProps {
  days: number;
  translations: {
    kpis: {
      totalAnalyses: string;
      activeUsers: string;
      documentsProcessed: string;
    };
    sections: {
      recentActivity: string;
      recentActivityDesc: string;
    };
    activity: {
      found: string;
      issues: string;
    };
  };
}

// Skeleton loader component
function SkeletonLoader({ className }: { className?: string }) {
  return (
    <div className={cn('animate-pulse bg-slate-200 dark:bg-slate-700 rounded', className)} />
  );
}

// KPI Card Component
function KpiCard({
  label,
  value,
  icon,
  color,
  isLoading,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color: 'sky' | 'green' | 'purple' | 'pink';
  isLoading: boolean;
}) {
  const colorConfig = {
    sky: 'from-sky-500 to-blue-500',
    green: 'from-green-500 to-emerald-500',
    purple: 'from-purple-500 to-violet-500',
    pink: 'from-pink-500 to-rose-500',
  }[color];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9, y: 20 }}
      animate={isLoading ? { opacity: 0, scale: 0.9, y: 20 } : { opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="rounded-xl border bg-white dark:bg-slate-900 p-4 shadow-sm"
    >
      {isLoading ? (
        <div className="space-y-3">
          <SkeletonLoader className="w-10 h-10 rounded-xl" />
          <div>
            <SkeletonLoader className="h-8 w-20 mb-2" />
            <SkeletonLoader className="h-3 w-24" />
          </div>
        </div>
      ) : (
        <>
          <div className={cn('w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center text-white', colorConfig)}>
            {icon}
          </div>
          <div className="mt-3">
            <p className="text-2xl font-bold text-slate-800 dark:text-white">
              {typeof value === 'number' ? value.toLocaleString() : value}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{label}</p>
          </div>
        </>
      )}
    </motion.div>
  );
}

export default function OverviewTab({ days, translations }: OverviewTabProps) {
  const [activityPage, setActivityPage] = useState(1);
  const { kpis, isLoading: kpisLoading, error: kpisError } = useAdminKPIs(days);
  const { data: activityData, isLoading: activityLoading, error: activityError } = useAdminActivity(activityPage, 20, days);

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label={translations.kpis.totalAnalyses}
          value={kpis?.total_analyses ?? 0}
          icon={<BarChart3 className="w-5 h-5" />}
          color="sky"
          isLoading={kpisLoading}
        />
        <KpiCard
          label={translations.kpis.activeUsers}
          value={kpis?.active_users ?? 0}
          icon={<Users className="w-5 h-5" />}
          color="pink"
          isLoading={kpisLoading}
        />
        <KpiCard
          label={translations.kpis.documentsProcessed}
          value={kpis?.documents_processed ?? 0}
          icon={<FileText className="w-5 h-5" />}
          color="purple"
          isLoading={kpisLoading}
        />
        <KpiCard
          label="Total Users"
          value={kpis?.total_users ?? 0}
          icon={<Users className="w-5 h-5" />}
          color="green"
          isLoading={kpisLoading}
        />
      </div>

      {/* Error states */}
      {kpisError && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400 text-sm">
          Failed to load KPIs. Please try again.
        </div>
      )}

      {/* Activity Table */}
      <div className="rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-semibold text-slate-800 dark:text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-pride-purple" />
              {translations.sections.recentActivity}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {translations.sections.recentActivityDesc}
            </p>
          </div>
        </div>

        {activityLoading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
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
        ) : activityError ? (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400 text-sm">
            Failed to load activity. Please try again.
          </div>
        ) : activityData?.activity.length === 0 ? (
          <div className="p-8 text-center text-slate-500 dark:text-slate-400">
            No recent activity
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800">
                  <th className="py-2 pr-4 font-medium">User</th>
                  <th className="py-2 pr-4 font-medium">Document</th>
                  <th className="py-2 pr-4 font-medium">Date</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 font-medium">Issues</th>
                </tr>
              </thead>
              <tbody>
                {activityData?.activity.map((item, idx) => (
                  <motion.tr
                    key={item.run_id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="border-b border-slate-50 dark:border-slate-800/50 last:border-0"
                  >
                    <td className="py-3 pr-4 text-slate-800 dark:text-white">{item.user_email}</td>
                    <td className="py-3 pr-4 text-slate-600 dark:text-slate-400 truncate max-w-[200px]">
                      {item.document_name || 'Direct text'}
                    </td>
                    <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">
                      {new Date(item.started_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 pr-4">
                      <span className={cn(
                        'px-2 py-0.5 rounded-full text-xs font-medium',
                        item.status === 'completed'
                          ? 'bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400'
                          : 'bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400'
                      )}>
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className="font-semibold text-slate-800 dark:text-white">{item.issue_count}</span>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {activityData && activityData.total_pages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
            <span className="text-sm text-slate-500 dark:text-slate-400">
              Page {activityData.page} of {activityData.total_pages}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActivityPage((p) => Math.max(1, p - 1))}
                disabled={activityPage === 1}
                className="p-2 rounded-lg border bg-white dark:bg-slate-800 disabled:opacity-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setActivityPage((p) => Math.min(activityData.total_pages, p + 1))}
                disabled={activityPage === activityData.total_pages}
                className="p-2 rounded-lg border bg-white dark:bg-slate-800 disabled:opacity-50"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
