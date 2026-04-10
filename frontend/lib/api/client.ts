import type { Annotation } from '@/components/AnnotatedText';
import type { Result } from '@/components/ResultCard';
import type { Severity } from '@/components/SeverityBadge';
import { toast } from 'sonner';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Fetch wrapper that handles 401 responses with toast and redirect
export async function fetchWithAuth(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = typeof window !== 'undefined'
    ? localStorage.getItem('auth_token')
    : null;

  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  if (response.status === 401) {
    // Clear auth state
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_token_expiry');

      // Show toast
      toast.error('Session expired. Please log in again.');

      // Get current locale from URL
      const pathParts = window.location.pathname.split('/');
      const locale = pathParts[1] === 'he' ? 'he' : 'en';

      // Redirect with return URL
      const returnUrl = encodeURIComponent(window.location.pathname);
      window.location.href = `/${locale}/login?returnUrl=${returnUrl}`;
    }

    throw new Error('Session expired');
  }

  return response;
}

// Types matching backend response
interface BackendIssue {
  type: string;
  severity: string;
  description: string;
  suggestion?: string;
  flagged_text?: string;
  start?: number;
  end?: number;
  confidence?: number;
}

interface BackendAnalysisResponse {
  original_text: string;
  analysis_status: string;
  issues_found: BackendIssue[];
  corrected_text?: string;
  note?: string;
  analysis_mode?: 'llm' | 'hybrid' | 'rules_only';
}

// Frontend analysis result
export interface AnalysisResult {
  annotations: Annotation[];
  results: Result[];
  counts: Record<Severity, number>;
  originalText: string;
  correctedText?: string;
  analysisMode?: 'llm' | 'hybrid' | 'rules_only';
}

// Map backend severity to frontend severity
function mapSeverity(backendSeverity: string): Severity {
  const severityMap: Record<string, Severity> = {
    'low': 'outdated',
    'medium': 'biased',
    'high': 'potentially_offensive',
    'critical': 'factually_incorrect',
    'outdated': 'outdated',
    'biased': 'biased',
    'potentially_offensive': 'potentially_offensive',
    'factually_incorrect': 'factually_incorrect',
    'gender bias': 'biased',
    'medicalization': 'outdated',
  };
  return severityMap[backendSeverity.toLowerCase()] || 'biased';
}

// Find all occurrences of a phrase in text
function findOccurrences(text: string, phrase: string): Array<{ start: number; end: number }> {
  const occurrences: Array<{ start: number; end: number }> = [];
  const lowerText = text.toLowerCase();
  const lowerPhrase = phrase.toLowerCase();
  let idx = 0;

  while (idx !== -1) {
    idx = lowerText.indexOf(lowerPhrase, idx);
    if (idx !== -1) {
      occurrences.push({ start: idx, end: idx + phrase.length });
      idx += phrase.length;
    }
  }

  return occurrences;
}

// Transform backend response to frontend format
function transformResponse(response: BackendAnalysisResponse, inputText: string): AnalysisResult {
  const annotations: Annotation[] = [];
  const results: Result[] = [];
  const counts: Record<Severity, number> = {
    outdated: 0,
    biased: 0,
    potentially_offensive: 0,
    factually_incorrect: 0,
  };

  for (const issue of response.issues_found) {
    const severity = mapSeverity(issue.severity || issue.type);
    const phrase = issue.flagged_text || issue.type || 'Issue';

    // Add to results (unique per phrase)
    const existingResult = results.find(r => r.phrase.toLowerCase() === phrase.toLowerCase());
    if (!existingResult) {
      results.push({
        phrase,
        severity,
        explanation: issue.description,
        suggestion: issue.suggestion,
        references: [
          { label: 'LGBTQ+ Language Guide', url: 'https://www.glaad.org/reference' },
        ],
      });
    }

    // Find occurrences in text and create annotations
    if (issue.start !== undefined && issue.end !== undefined) {
      // Use exact positions if provided
      annotations.push({
        start: issue.start,
        end: issue.end,
        severity,
        label: phrase,
        explanation: issue.description,
        suggestion: issue.suggestion,
        confidence: issue.confidence,
        references: [
          { label: 'LGBTQ+ Language Guide', url: 'https://www.glaad.org/reference' },
        ],
      });
      counts[severity] += 1;
    } else {
      // Find all occurrences in text
      const occurrences = findOccurrences(inputText, phrase);
      for (const occ of occurrences) {
        annotations.push({
          start: occ.start,
          end: occ.end,
          severity,
          label: phrase,
          explanation: issue.description,
          suggestion: issue.suggestion,
          confidence: issue.confidence,
          references: [
            { label: 'LGBTQ+ Language Guide', url: 'https://www.glaad.org/reference' },
          ],
        });
        counts[severity] += 1;
      }
    }
  }

  return {
    annotations,
    results,
    counts,
    originalText: response.original_text,
    correctedText: response.corrected_text,
    analysisMode: response.analysis_mode,
  };
}

// Main API function
export async function analyzeText(
  text: string,
  options?: {
    language?: 'en' | 'he' | 'auto';
    privateMode?: boolean;
    useAuth?: boolean;
    filename?: string;
  }
): Promise<AnalysisResult> {
  const fetchFn = options?.useAuth ? fetchWithAuth : fetch;
  const response = await fetchFn(`${API_BASE_URL}/api/v1/analysis/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      language: options?.language || 'auto',
      private_mode: options?.privateMode ?? true,
      filename: options?.filename ?? null,
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Analysis failed: ${response.status} - ${errorText}`);
  }

  const data: BackendAnalysisResponse = await response.json();
  return transformResponse(data, text);
}

// Upload file and get extracted text
export async function uploadFile(file: File): Promise<{ text: string; filename: string; pageCount: number }> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/v1/ingestion/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    let detail = errorText;
    try {
      const parsed = JSON.parse(errorText);
      if (parsed.detail) detail = parsed.detail;
    } catch { /* not JSON, use raw text */ }
    throw new Error(`Upload failed: ${response.status} - ${detail}`);
  }

  const data = await response.json();
  return {
    text: data.full_text || data.text_preview || '',
    filename: data.filename,
    pageCount: data.page_count,
  };
}

// Health check
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/`);
    const data = await response.json();
    return data.status === 'OK';
  } catch {
    return false;
  }
}

export interface ModelHealthResult {
  available: boolean;
  model: string;
  responseTimeMs: number | null;
  circuitBreaker: 'closed' | 'open' | 'half_open';
  error?: string;
}

// History types
export interface HistoryItem {
  document_id: string;
  run_id: string;
  original_filename: string | null;
  language: string;
  created_at: string;
  input_type: 'paste' | 'upload';
  runtime_ms: number | null;
  total_findings: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  score: number | null;
  word_count: number | null;
  analysis_mode: 'llm' | 'hybrid' | 'rules_only' | null;
}

export interface HistoryResponse {
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export async function getHistory(limit = 20, offset = 0): Promise<HistoryResponse> {
  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/v1/history/?limit=${limit}&offset=${offset}`,
  );

  if (!response.ok) {
    const errorText = await response.text();
    let detail = errorText;
    try {
      const parsed = JSON.parse(errorText);
      if (parsed.detail) detail = parsed.detail;
    } catch { /* not JSON */ }
    throw new Error(`Failed to load history: ${response.status} - ${detail}`);
  }

  return response.json() as Promise<HistoryResponse>;
}

// Check vLLM model availability and circuit breaker state
export async function modelHealthCheck(): Promise<ModelHealthResult> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/health/model`);
    const data = await response.json();
    return {
      available: data.status === 'available',
      model: data.model,
      responseTimeMs: data.response_time_ms ?? null,
      circuitBreaker: data.circuit_breaker,
      error: data.error,
    };
  } catch {
    return {
      available: false,
      model: 'unknown',
      responseTimeMs: null,
      circuitBreaker: 'open',
      error: 'Could not reach backend',
    };
  }
}
