'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Building2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAdminOrgs } from '@/lib/api/admin';

interface OrganizationsTabProps {
  translations: {
    orgs?: {
      noResults: string;
    };
  };
}

// Skeleton loader component
function SkeletonLoader({ className }: { className?: string }) {
  return (
    <div className={cn('animate-pulse bg-slate-200 dark:bg-slate-700 rounded', className)} />
  );
}

export default function OrganizationsTab({ translations }: OrganizationsTabProps) {
  const [page, setPage] = useState(1);
  const { data, isLoading, error } = useAdminOrgs(page, 20);

  return (
    <div className="space-y-4">
      {/* Organizations Table */}
      <div className="rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Building2 className="w-5 h-5 text-pride-purple" />
          <h3 className="font-semibold text-slate-800 dark:text-white">Organizations</h3>
          {data && (
            <span className="text-sm text-slate-500 dark:text-slate-400">
              ({data.total} total)
            </span>
          )}
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-4 py-3 border-b border-slate-50 dark:border-slate-800/50">
                <SkeletonLoader className="h-4 w-48" />
                <SkeletonLoader className="h-4 w-24" />
                <SkeletonLoader className="h-4 w-20" />
                <SkeletonLoader className="h-4 w-24" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400 text-sm">
            Failed to load organizations. Please try again.
          </div>
        ) : data?.organizations.length === 0 ? (
          <div className="p-8 text-center text-slate-500 dark:text-slate-400">
            {translations.orgs?.noResults || 'No organizations found'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800">
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Slug</th>
                  <th className="py-2 pr-4 font-medium">Users</th>
                  <th className="py-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {data?.organizations.map((org, idx) => (
                  <motion.tr
                    key={org.org_id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    className="border-b border-slate-50 dark:border-slate-800/50 last:border-0"
                  >
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-pride-purple/10 flex items-center justify-center">
                          <Building2 className="w-4 h-4 text-pride-purple" />
                        </div>
                        <span className="font-medium text-slate-800 dark:text-white">{org.name}</span>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">
                      {org.slug || '-'}
                    </td>
                    <td className="py-3 pr-4">
                      <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400 text-xs font-medium">
                        {org.user_count} users
                      </span>
                    </td>
                    <td className="py-3 text-slate-500 dark:text-slate-400">
                      {new Date(org.created_at).toLocaleDateString()}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
            <span className="text-sm text-slate-500 dark:text-slate-400">
              Page {data.page} of {data.total_pages}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded-lg border bg-white dark:bg-slate-800 disabled:opacity-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                disabled={page === data.total_pages}
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
