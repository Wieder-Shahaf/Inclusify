'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Users,
  Search,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAdminUsers } from '@/lib/api/admin';

interface UsersTabProps {
  translations: {
    users?: {
      searchPlaceholder: string;
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

export default function UsersTab({ translations }: UsersTabProps) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [institutionInput, setInstitutionInput] = useState('');
  const [institution, setInstitution] = useState('');
  const [minAnalyses, setMinAnalyses] = useState<number | undefined>(undefined);
  const { data, isLoading, error } = useAdminUsers(page, 20, search || undefined, institution || undefined, minAnalyses);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setInstitution(institutionInput);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      {/* Filters */}
      <form onSubmit={handleSearch} className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={translations.users?.searchPlaceholder || 'Search by email...'}
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple/50"
          />
        </div>
        <input
          type="text"
          value={institutionInput}
          onChange={(e) => setInstitutionInput(e.target.value)}
          placeholder="Institution..."
          className="flex-1 min-w-[160px] max-w-xs px-4 py-2 rounded-lg border bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple/50"
        />
        <select
          value={minAnalyses ?? ''}
          onChange={(e) => setMinAnalyses(e.target.value ? Number(e.target.value) : undefined)}
          className="px-3 py-2 rounded-lg border bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple/50"
        >
          <option value="">Any analyses</option>
          <option value="1">1+ analyses</option>
          <option value="5">5+ analyses</option>
          <option value="10">10+ analyses</option>
        </select>
        <button
          type="submit"
          className="px-4 py-2 rounded-lg bg-pride-purple text-white text-sm font-medium hover:bg-pride-purple/90 transition-colors"
        >
          Search
        </button>
      </form>

      {/* Users Table */}
      <div className="rounded-2xl border bg-white dark:bg-slate-900 shadow-sm overflow-hidden">
        <div className="flex items-center gap-2 px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <Users className="w-5 h-5 text-pride-purple" />
          <h3 className="font-semibold text-slate-800 dark:text-white">Users</h3>
          {data && (
            <span className="text-sm text-slate-400">({data.total} total)</span>
          )}
        </div>

        {isLoading ? (
          <div className="p-6 space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-6">
                <SkeletonLoader className="h-4 w-48" />
                <SkeletonLoader className="h-4 w-24" />
                <SkeletonLoader className="h-4 w-24" />
                <SkeletonLoader className="h-4 w-24" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="p-6 text-red-500 dark:text-red-400 text-sm">
            Failed to load users. Please try again.
          </div>
        ) : data?.users.length === 0 ? (
          <div className="py-16 text-center text-slate-500 dark:text-slate-400">
            {translations.users?.noResults || 'No users found'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide bg-slate-50/70 dark:bg-slate-800/40 border-b border-slate-100 dark:border-slate-800">
                  <th className="px-6 py-3">Email</th>
                  <th className="px-4 py-3 w-36">Role</th>
                  <th className="px-4 py-3 w-36">Last Login</th>
                  <th className="px-4 py-3 w-36">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 dark:divide-slate-800/50">
                {data?.users.map((user, idx) => (
                  <motion.tr
                    key={user.user_id}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    className="hover:bg-slate-50/60 dark:hover:bg-slate-800/20 transition-colors"
                  >
                    <td className="px-6 py-4 font-medium text-slate-800 dark:text-white">{user.email}</td>
                    <td className="px-4 py-4">
                      <span className={cn(
                        'px-2.5 py-1 rounded-full text-xs font-medium',
                        user.role === 'site_admin'
                          ? 'bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400 border border-purple-200 dark:border-purple-800'
                          : 'bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700'
                      )}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-slate-500 dark:text-slate-400">
                      {user.last_login_at
                        ? new Date(user.last_login_at).toLocaleDateString()
                        : <span className="italic text-slate-300 dark:text-slate-600">Never</span>}
                    </td>
                    <td className="px-4 py-4 text-slate-500 dark:text-slate-400">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20">
            <span className="text-sm text-slate-500 dark:text-slate-400">
              Page {data.page} of {data.total_pages} &nbsp;·&nbsp; {data.total} total
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 rounded-lg border bg-white dark:bg-slate-800 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                disabled={page === data.total_pages}
                className="p-2 rounded-lg border bg-white dark:bg-slate-800 disabled:opacity-40 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
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
