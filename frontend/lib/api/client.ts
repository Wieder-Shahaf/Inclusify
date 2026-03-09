import type { Annotation } from '@/components/AnnotatedText';
import type { Result } from '@/components/ResultCard';
import type { Severity } from '@/components/SeverityBadge';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Types matching backend response
interface BackendIssue {
  type: string;
  severity: string;
  description: string;
  suggestion?: string;
  span?: string;
  start?: number;
  end?: number;
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
    'high': 'offensive',
    'critical': 'incorrect',
    'outdated': 'outdated',
    'biased': 'biased',
    'offensive': 'offensive',
    'incorrect': 'incorrect',
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
    offensive: 0,
    incorrect: 0,
  };

  for (const issue of response.issues_found) {
    const severity = mapSeverity(issue.severity || issue.type);
    const phrase = issue.span || issue.type || 'Issue';

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
  }
): Promise<AnalysisResult> {
  const response = await fetch(`${API_BASE_URL}/api/v1/analysis/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      language: options?.language || 'auto',
      private_mode: options?.privateMode ?? true,
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
    throw new Error(`Upload failed: ${response.status} - ${errorText}`);
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
