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
  const { data, isLoading, error, refresh } = useAdminUsers(page, 20, search || undefined);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  return (
    <div className="space-y-4">
      {/* Search */}
      <form onSubmit={handleSearch} className="flex items-center gap-2">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={translations.users?.searchPlaceholder || 'Search by email...'}
            className="w-full pl-10 pr-4 py-2 rounded-lg border bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple/50"
          />
        </div>
        <button
          type="submit"
          className="px-4 py-2 rounded-lg bg-pride-purple text-white text-sm font-medium hover:bg-pride-purple/90 transition-colors"
        >
          Search
        </button>
      </form>

      {/* Users Table */}
      <div className="rounded-2xl border bg-white dark:bg-slate-900 p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Users className="w-5 h-5 text-pride-purple" />
          <h3 className="font-semibold text-slate-800 dark:text-white">Users</h3>
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
                <SkeletonLoader className="h-4 w-32" />
                <SkeletonLoader className="h-4 w-20" />
                <SkeletonLoader className="h-4 w-24" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400 text-sm">
            Failed to load users. Please try again.
          </div>
        ) : data?.users.length === 0 ? (
          <div className="p-8 text-center text-slate-500 dark:text-slate-400">
            {translations.users?.noResults || 'No users found'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800">
                  <th className="py-2 pr-4 font-medium">Email</th>
                  <th className="py-2 pr-4 font-medium">Organization</th>
                  <th className="py-2 pr-4 font-medium">Role</th>
                  <th className="py-2 pr-4 font-medium">Last Login</th>
                  <th className="py-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {data?.users.map((user, idx) => (
                  <motion.tr
                    key={user.user_id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    className="border-b border-slate-50 dark:border-slate-800/50 last:border-0"
                  >
                    <td className="py-3 pr-4 font-medium text-slate-800 dark:text-white">{user.email}</td>
                    <td className="py-3 pr-4 text-slate-600 dark:text-slate-400">{user.org_name || '-'}</td>
                    <td className="py-3 pr-4">
                      <span className={cn(
                        'px-2 py-0.5 rounded-full text-xs font-medium',
                        user.role === 'site_admin'
                          ? 'bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400'
                          : user.role === 'org_admin'
                          ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                          : 'bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                      )}>
                        {user.role}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-slate-500 dark:text-slate-400">
                      {user.last_login_at
                        ? new Date(user.last_login_at).toLocaleDateString()
                        : 'Never'}
                    </td>
                    <td className="py-3 text-slate-500 dark:text-slate-400">
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
