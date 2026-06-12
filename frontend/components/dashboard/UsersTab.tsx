'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Users,
  Search,
  ChevronLeft,
  ChevronRight,
  ShieldPlus,
  ShieldMinus,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useAdminUsers, updateUserRole } from '@/lib/api/admin';
import { useAuth } from '@/contexts/AuthContext';
import ConfirmDialog from '@/components/ConfirmDialog';

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

interface PendingRoleChange {
  userId: string;
  email: string;
  newRole: 'user' | 'site_admin';
}

export default function UsersTab({ translations }: UsersTabProps) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [institutionInput, setInstitutionInput] = useState('');
  const [institution, setInstitution] = useState('');
  const [minAnalyses, setMinAnalyses] = useState<number | undefined>(undefined);
  const { data, isLoading, error, refresh } = useAdminUsers(page, 5, search || undefined, institution || undefined, minAnalyses);
  const { user: currentUser } = useAuth();
  const [pendingRoleChange, setPendingRoleChange] = useState<PendingRoleChange | null>(null);
  const [roleUpdating, setRoleUpdating] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setInstitution(institutionInput);
    setPage(1);
  };

  const handleConfirmRoleChange = async () => {
    if (!pendingRoleChange || roleUpdating) return;
    setRoleUpdating(true);
    try {
      await updateUserRole(pendingRoleChange.userId, pendingRoleChange.newRole);
      toast.success(
        pendingRoleChange.newRole === 'site_admin'
          ? `${pendingRoleChange.email} is now an admin`
          : `${pendingRoleChange.email} is no longer an admin`,
      );
      refresh();
    } catch {
      toast.error('Failed to update role. Please try again.');
    } finally {
      setRoleUpdating(false);
      setPendingRoleChange(null);
    }
  };

  return (
    <div className="flex h-full min-w-0 flex-col gap-3 overflow-hidden">
      {/* Filters */}
      <form onSubmit={handleSearch} className="flex shrink-0 flex-wrap items-center gap-3">
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
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border bg-white dark:bg-slate-900 shadow-sm">
        <div className="flex shrink-0 items-center gap-2 px-5 py-3 border-b border-slate-100 dark:border-slate-800">
          <Users className="w-5 h-5 text-pride-purple" />
          <h3 className="font-semibold text-slate-800 dark:text-white">Users</h3>
          {data && (
            <span className="text-sm text-slate-400">({data.total} total)</span>
          )}
        </div>

        {isLoading ? (
          <div className="min-h-0 flex-1 space-y-4 overflow-hidden p-5">
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
          <div className="min-h-0 flex-1 overflow-x-auto overflow-y-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide bg-slate-50/70 dark:bg-slate-800/40 border-b border-slate-100 dark:border-slate-800">
                  <th className="px-6 py-3">Email</th>
                  <th className="px-4 py-3 w-44">Institution</th>
                  <th className="px-4 py-3 w-32">Role</th>
                  <th className="px-4 py-3 w-28">Analyses</th>
                  <th className="px-4 py-3 w-36">Last Login</th>
                  <th className="px-4 py-3 w-36">Created</th>
                  <th className="px-4 py-3 w-44">Actions</th>
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
                    <td className="px-6 py-3 font-medium text-slate-800 dark:text-white">{user.email}</td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                      <span className="block max-w-[160px] truncate">
                        {user.institution || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        'px-2.5 py-1 rounded-full text-xs font-medium',
                        user.role === 'site_admin'
                          ? 'bg-purple-50 text-purple-600 dark:bg-purple-900/20 dark:text-purple-400 border border-purple-200 dark:border-purple-800'
                          : 'bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700'
                      )}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-semibold tabular-nums text-slate-800 dark:text-white">
                      {user.analysis_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                      {user.last_login_at
                        ? new Date(user.last_login_at).toLocaleDateString()
                        : <span className="italic text-slate-300 dark:text-slate-600">Never</span>}
                    </td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      {user.user_id === currentUser?.id ? (
                        <span className="text-xs italic text-slate-300 dark:text-slate-600">You</span>
                      ) : user.role === 'site_admin' ? (
                        <button
                          onClick={() => setPendingRoleChange({ userId: user.user_id, email: user.email, newRole: 'user' })}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:border-red-300 hover:text-red-500 dark:hover:border-red-800 transition-colors"
                        >
                          <ShieldMinus className="w-3.5 h-3.5" />
                          Remove Admin
                        </button>
                      ) : (
                        <button
                          onClick={() => setPendingRoleChange({ userId: user.user_id, email: user.email, newRole: 'site_admin' })}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border border-purple-200 dark:border-purple-800 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 transition-colors"
                        >
                          <ShieldPlus className="w-3.5 h-3.5" />
                          Promote to Admin
                        </button>
                      )}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="flex shrink-0 items-center justify-between px-5 py-3 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20">
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

      <ConfirmDialog
        open={pendingRoleChange !== null}
        title={pendingRoleChange?.newRole === 'site_admin' ? 'Promote to Admin?' : 'Remove admin role?'}
        description={
          pendingRoleChange?.newRole === 'site_admin'
            ? `${pendingRoleChange?.email ?? ''} will get full access to the dashboard, user management, and analytics. The change takes effect on their next login.`
            : `${pendingRoleChange?.email ?? ''} will lose access to the dashboard. The change takes effect on their next login.`
        }
        confirmLabel={pendingRoleChange?.newRole === 'site_admin' ? 'Promote' : 'Remove Admin'}
        cancelLabel="Cancel"
        variant={pendingRoleChange?.newRole === 'site_admin' ? 'default' : 'danger'}
        onConfirm={handleConfirmRoleChange}
        onCancel={() => { if (!roleUpdating) setPendingRoleChange(null); }}
      />
    </div>
  );
}
