import useSWR from 'swr';
import { fetchWithAuth } from './client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Types matching backend response schemas (from 06-01)
export interface AnalyticsResponse {
  total_users: number;
  active_users: number;
  total_analyses: number;
  documents_processed: number;
}

export interface UserItem {
  user_id: string;
  email: string;
  role: string;
  last_login_at: string | null;
  created_at: string;
}

export interface UsersListResponse {
  users: UserItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ActivityItem {
  run_id: string;
  user_email: string;
  document_name: string | null;
  started_at: string;
  status: string;
  issue_count: number;
}

export interface ActivityResponse {
  activity: ActivityItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// SWR fetcher using authenticated requests
const fetcher = async (url: string) => {
  const response = await fetchWithAuth(url);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
};

// SWR hooks with caching
export function useAdminKPIs(days: number) {
  const { data, error, isLoading, mutate } = useSWR<AnalyticsResponse>(
    `${API_BASE_URL}/api/v1/admin/analytics?days=${days}`,
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 60000 }
  );
  return { kpis: data, isLoading, error, refresh: mutate };
}

export function useAdminUsers(
  page: number,
  pageSize: number = 20,
  search?: string,
  institution?: string,
  minAnalyses?: number,
) {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (search) params.set('search', search);
  if (institution) params.set('institution', institution);
  if (minAnalyses !== undefined && minAnalyses > 0) params.set('min_analyses', String(minAnalyses));
  const { data, error, isLoading, mutate } = useSWR<UsersListResponse>(
    `${API_BASE_URL}/api/v1/admin/users?${params.toString()}`,
    fetcher,
    { revalidateOnFocus: false }
  );
  return { data, isLoading, error, refresh: mutate };
}

export function useAdminActivity(page: number, pageSize: number = 20, days: number = 30) {
  const { data, error, isLoading, mutate } = useSWR<ActivityResponse>(
    `${API_BASE_URL}/api/v1/admin/activity?page=${page}&page_size=${pageSize}&days=${days}`,
    fetcher,
    { revalidateOnFocus: false }
  );
  return { data, isLoading, error, refresh: mutate };
}

export interface ModelMetricsResponse {
  total_analyses: number;
  total_llm_calls: number;
  total_errors: number;
  error_rate: number;
  fallback_rate: number;
  avg_latency_ms: number | null;
  min_latency_ms: number | null;
  max_latency_ms: number | null;
  mode_llm: number;
  mode_hybrid: number;
  mode_rules_only: number;
}

export function useModelMetrics(days: number) {
  const { data, error, isLoading, mutate } = useSWR<ModelMetricsResponse>(
    `${API_BASE_URL}/api/v1/admin/model-metrics?days=${days}`,
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 60000 }
  );
  return { data, isLoading, error, refresh: mutate };
}

export interface TopPhrase { phrase: string; count: number; }
export interface FrequencyTrendItem {
  category: string;
  count: number;
  top_phrases: TopPhrase[];
}
export interface FrequencyTrendsResponse {
  trends: FrequencyTrendItem[];
  days: number;
}

export function useAdminFrequencyTrends(days: number) {
  const { data, error, isLoading, mutate } = useSWR<FrequencyTrendsResponse>(
    `${API_BASE_URL}/api/v1/admin/frequency-trends?days=${days}`,
    fetcher,
    { revalidateOnFocus: false, dedupingInterval: 60000 }
  );
  return { data, isLoading, error, refresh: mutate };
}
