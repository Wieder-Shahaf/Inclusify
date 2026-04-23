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
  inclusive_sentence?: string;
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
  run_id?: string;
}

// Frontend analysis result
export interface AnalysisResult {
  annotations: Annotation[];
  results: Result[];
  counts: Record<Severity, number>;
  originalText: string;
  correctedText?: string;
  analysisMode?: 'llm' | 'hybrid' | 'rules_only';
  runId?: string;
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
        inclusive_sentence: issue.inclusive_sentence,
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
    runId: response.run_id,
  };
}

export interface BboxAnnotation {
  start: number;
  end: number;
  page: number;
  bbox: { l: number; t: number; r: number; b: number };
}

export interface PageSize {
  width: number;
  height: number;
}

export interface FileMetadata {
  filename: string;
  mimeType: string;
  inputType: 'pdf' | 'docx' | 'pptx' | 'txt';
  pageCount: number;
  title?: string | null;
  author?: string | null;
  detectedLanguage?: string | null;
  fileStorageRef?: string | null;
  chunks?: string[] | null;
}

export interface UploadResult extends FileMetadata {
  text: string;
  chunks?: string[] | null;
  bboxAnnotations?: BboxAnnotation[] | null;
  pageSizes?: Record<string, PageSize> | null;
  markdownText?: string | null;
}

// Main API function
export async function analyzeText(
  text: string,
  options?: {
    language?: 'en' | 'he' | 'auto';
    privateMode?: boolean;
    useAuth?: boolean;
    fileMeta?: FileMetadata;
  }
): Promise<AnalysisResult> {
  const fetchFn = options?.useAuth ? fetchWithAuth : fetch;
  const meta = options?.fileMeta;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 4 * 60 * 1000); // 4 min safety cap

  let response: Response;
  try {
    response = await fetchFn(`${API_BASE_URL}/api/v1/analysis/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
      body: JSON.stringify({
        text,
        language: options?.language || 'auto',
        private_mode: options?.privateMode ?? true,
        input_type: meta?.inputType ?? null,
        original_filename: meta?.filename ?? null,
        mime_type: meta?.mimeType ?? null,
        page_count: meta?.pageCount ?? null,
        title: meta?.title ?? null,
        author: meta?.author ?? null,
        detected_language: meta?.detectedLanguage ?? null,
        file_storage_ref: meta?.fileStorageRef ?? null,
        chunks: meta?.chunks ?? null,
      }),
    });
  } catch (err) {
    if (err instanceof Error && err.name === 'AbortError') {
      throw new Error('Analysis timed out. The server is taking too long — please try again.');
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Analysis failed: ${response.status} - ${errorText}`);
  }

  const data: BackendAnalysisResponse = await response.json();
  return transformResponse(data, text);
}

function _extToInputType(filename: string): FileMetadata['inputType'] {
  const ext = filename.split('.').pop()?.toLowerCase();
  if (ext === 'pdf') return 'pdf';
  if (ext === 'docx') return 'docx';
  if (ext === 'pptx') return 'pptx';
  return 'txt';
}

// Upload file and get extracted text + all Docling metadata
export async function uploadFile(file: File): Promise<UploadResult> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetchWithAuth(`${API_BASE_URL}/api/v1/ingestion/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Upload failed: ${response.status} - ${errorText}`);
  }

  const data = await response.json();
  return {
    text: data.full_text || data.text_preview || '',
    filename: data.filename,
    mimeType: file.type,
    inputType: _extToInputType(data.filename),
    pageCount: data.page_count,
    title: data.title ?? null,
    author: data.author ?? null,
    detectedLanguage: data.detected_language ?? null,
    fileStorageRef: data.file_storage_ref ?? null,
    chunks: data.chunks ?? null,
    bboxAnnotations: data.bbox_annotations ?? null,
    pageSizes: data.page_sizes ?? null,
    markdownText: data.markdown_text ?? null,
  };
}

export interface HistoryEntry {
  run_id: string;
  document_id: string;
  title: string | null;
  filename: string | null;
  input_type: string;
  language: string | null;
  page_count: number | null;
  analyzed_at: string | null;
  runtime_ms: number | null;
  findings_count: number;
  findings_low: number;
  findings_medium: number;
  findings_high: number;
}

export interface HistoryKPIs {
  total_analyses: number;
  total_findings: number;
  avg_issues_per_doc: number;
  findings_low: number;
  findings_medium: number;
  findings_high: number;
}

export interface HistoryResponse {
  kpis: HistoryKPIs;
  analyses: HistoryEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface FindingDetail {
  finding_id: string;
  category: string;
  severity: 'low' | 'medium' | 'high';
  start_idx: number;
  end_idx: number;
  confidence: number | null;
  explanation: string | null;
  excerpt: string | null;
  suggestion: string | null;
}

export interface AnalysisDetail extends HistoryEntry {
  status: string;
  findings: FindingDetail[];
}

export async function getAnalysisDetail(runId: string): Promise<AnalysisDetail> {
  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/v1/users/me/history/${runId}`
  );
  if (!response.ok) throw new Error(`Failed to load analysis: ${response.status}`);
  return response.json();
}

export async function deleteAnalysis(runId: string): Promise<void> {
  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/v1/users/me/history/${runId}`,
    { method: 'DELETE' }
  );
  if (!response.ok) throw new Error(`Failed to delete analysis: ${response.status}`);
}

export async function getHistory(limit = 50, offset = 0): Promise<HistoryResponse> {
  const response = await fetchWithAuth(
    `${API_BASE_URL}/api/v1/users/me/history?limit=${limit}&offset=${offset}`
  );
  if (!response.ok) {
    throw new Error(`Failed to load history: ${response.status}`);
  }
  return response.json();
}

export interface FeedbackPayload {
  vote: 'up' | 'down';
  flaggedText: string;
  severity: string;
  startIdx: number;
  endIdx: number;
  findingId?: string;
  runId?: string;
  comment?: string;
}

export async function submitFeedback(payload: FeedbackPayload): Promise<void> {
  try {
    await fetchWithAuth(`${API_BASE_URL}/api/v1/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vote: payload.vote,
        flagged_text: payload.flaggedText,
        severity: payload.severity,
        start_idx: payload.startIdx,
        end_idx: payload.endIdx,
        finding_id: payload.findingId ?? null,
        run_id: payload.runId ?? null,
        comment: payload.comment ?? null,
      }),
    });
  } catch {
    // Feedback is best-effort — silently swallow errors
  }
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
