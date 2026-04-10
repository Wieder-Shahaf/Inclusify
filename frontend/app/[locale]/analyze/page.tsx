'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import SeverityBadge from '@/components/SeverityBadge';
import PaperUpload from '@/components/PaperUpload';
import ProcessingAnimation from '@/components/ProcessingAnimation';
import AnalysisSummary from '@/components/AnalysisSummary';
import IssueTooltip from '@/components/IssueTooltip';
import HealthWarningBanner from '@/components/HealthWarningBanner';
import { Annotation } from '@/components/AnnotatedText';
import { analyzeText, uploadFile, healthCheck, modelHealthCheck } from '@/lib/api/client';
import { useAuth } from '@/contexts/AuthContext';
import { useLiveAnnouncer } from '@/contexts/LiveAnnouncerContext';
import { useKeyboardNavigation } from '@/hooks/useKeyboardNavigation';
import { RotateCcw, FileText, ChevronLeft, ChevronRight, Scan, BarChart3, ShieldCheck, Lock, ArrowRight, Download } from 'lucide-react';
import { cn } from '@/lib/utils';
import PrivateModeToggle from '@/components/PrivateModeToggle';

type ViewState = 'upload' | 'processing' | 'results';

interface AnalysisData {
  text: string;
  annotations: Annotation[];
  results: Array<{
    phrase: string;
    severity: 'outdated' | 'biased' | 'potentially_offensive' | 'factually_incorrect';
    explanation: string;
    suggestion?: string;
    references?: Array<{ label: string; url: string }>;
  }>;
  counts: Record<'outdated' | 'biased' | 'potentially_offensive' | 'factually_incorrect', number>;
  summary: {
    totalIssues: number;
    score: number;
    recommendations: string[];
  };
}

const emptyAnalysis: AnalysisData = {
  text: '',
  annotations: [],
  results: [],
  counts: { outdated: 0, biased: 0, potentially_offensive: 0, factually_incorrect: 0 },
  summary: { totalIssues: 0, score: 100, recommendations: [] },
};

export default function AnalyzePage() {
  const t = useTranslations('analyzer');
  const locale = useLocale();
  const isHebrew = locale === 'he';
  const { user } = useAuth();
  const { announce } = useLiveAnnouncer();
  const issuesListRef = useRef<HTMLDivElement>(null);

  const [viewState, setViewState] = useState<ViewState>('upload');
  const [fileName, setFileName] = useState('');
  const [analysis, setAnalysis] = useState<AnalysisData>(emptyAnalysis);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [modelAvailable, setModelAvailable] = useState<boolean | null>(null);
  const [analysisMode, setAnalysisMode] = useState<'llm' | 'hybrid' | 'rules_only' | null>(null);
  const [showGuestPrompt, setShowGuestPrompt] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [processingStage, setProcessingStage] = useState<'uploading' | 'parsing' | 'analyzing' | 'generating' | 'complete'>('uploading');
  const [privateMode, setPrivateMode] = useState(false); // Default OFF per user decision
  const [filterSeverity, setFilterSeverity] = useState<'all' | 'outdated' | 'biased' | 'potentially_offensive' | 'factually_incorrect'>('all');

  // Health check on mount with 30-second polling
  useEffect(() => {
    const checkHealth = async () => {
      const healthy = await healthCheck();
      setBackendHealthy(healthy);
      if (healthy) {
        const model = await modelHealthCheck();
        setModelAvailable(model.available);
      } else {
        setModelAvailable(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Error handler that maps backend errors to user-friendly messages
  const handleApiError = useCallback((error: unknown) => {
    let message = t('errors.generic');

    if (error instanceof Error) {
      const errorText = error.message.toLowerCase();
      if (errorText.includes('password-protected') || errorText.includes('password')) {
        message = t('errors.passwordProtected');
      } else if (errorText.includes('corrupted')) {
        message = t('errors.corruptedFile');
      } else if (errorText.includes('50 pages') || errorText.includes('page limit')) {
        message = t('errors.tooManyPages');
      } else if (errorText.includes('50mb') || errorText.includes('file size')) {
        message = t('errors.fileTooLarge');
      } else if (errorText.includes('upload')) {
        message = t('errors.uploadFailed');
      }
    }

    setErrorMessage(message);
    setViewState('upload');
    announce(message, 'assertive');
  }, [t, announce]);

  const handleFileSelect = useCallback(async (file: File) => {
    setErrorMessage(null);  // Clear any previous error
    setFileName(file.name);
    setViewState('processing');
    announce(t('a11y.uploadStarted'));

    // Real API path
    try {
      setProcessingStage('uploading');

      // Upload and extract text
      const uploadResult = await uploadFile(file);

      setProcessingStage('analyzing');

      // Analyze the extracted text
      const result = await analyzeText(uploadResult.text, {
        language: locale as 'en' | 'he' | 'auto',
        privateMode: privateMode,
        useAuth: true,
      });

      setProcessingStage('complete');

      // Calculate score using severity weights (offensive > incorrect > biased > outdated)
      const weights = { outdated: 1, biased: 2, factually_incorrect: 3, potentially_offensive: 4 };
      const wordCount = uploadResult.text.split(/\s+/).filter(Boolean).length;
      const totalWeightedIssues =
        result.counts.outdated * weights.outdated +
        result.counts.biased * weights.biased +
        result.counts.factually_incorrect * weights.factually_incorrect +
        result.counts.potentially_offensive * weights.potentially_offensive;
      const score = Math.max(0, Math.round(100 - (totalWeightedIssues / Math.max(wordCount, 1)) * 200));

      // Generate recommendations based on issue counts
      const recommendations: string[] = [];
      if (result.counts.potentially_offensive > 0) recommendations.push(t('recommendations.potentially_offensive'));
      if (result.counts.factually_incorrect > 0) recommendations.push(t('recommendations.factually_incorrect'));
      if (result.counts.biased > 0) recommendations.push(t('recommendations.biased'));
      if (result.counts.outdated > 0) recommendations.push(t('recommendations.outdated'));
      if (recommendations.length === 0) recommendations.push(t('recommendations.excellent'));

      setAnalysis({
        text: uploadResult.text,
        annotations: result.annotations,
        results: result.results,
        counts: result.counts,
        summary: {
          totalIssues: Object.values(result.counts).reduce((a, b) => a + b, 0),
          score,
          recommendations,
        },
      });
      setAnalysisMode(result.analysisMode || null);
      setViewState('results');
      announce(t('a11y.analysisComplete', { count: Object.values(result.counts).reduce((a, b) => a + b, 0) }));
    } catch (error) {
      console.error('Analysis failed:', error);
      handleApiError(error);
    }
  }, [locale, t, handleApiError, privateMode, announce]);

  const handleReset = useCallback(() => {
    setViewState('upload');
    setFileName('');
    setAnalysis(emptyAnalysis);
    setAnalysisMode(null);
    setErrorMessage(null);
    setProcessingStage('uploading');
    setShowGuestPrompt(true);
    setPrivateMode(false);
    setFilterSeverity('all');
  }, []);

  const handleIssueClick = useCallback((result: AnalysisData['results'][0]) => {
    const annotation = analysis.annotations.find(
      (a) => a.label.toLowerCase() === result.phrase.toLowerCase()
    );
    if (annotation) {
      // Scroll the text panel to the highlighted span
      setTimeout(() => {
        document.getElementById(`ann-${annotation.start}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 50);
    }
  }, [analysis.annotations]);

  const exportCSV = useCallback(() => {
    const esc = (s: string) => `"${s.replace(/"/g, '""')}"`;
    const headers = ['Flagged Term', 'Severity', 'Explanation', 'Suggestion'];
    const rows = analysis.results.map(r => [
      esc(r.phrase), esc(r.severity), esc(r.explanation), esc(r.suggestion || ''),
    ]);
    const csv = '\ufeff' + [headers, ...rows].map(r => r.join(',')).join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${fileName.replace(/\.[^/.]+$/, '')}_inclusify.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [analysis.results, fileName]);

  const exportPDF = useCallback(() => {
    const win = window.open('', '_blank');
    if (!win) return;
    const severityColor: Record<string, string> = {
      outdated: '#0ea5e9', biased: '#f59e0b',
      potentially_offensive: '#f43f5e', factually_incorrect: '#ef4444',
    };
    const severityLabel: Record<string, string> = {
      outdated: 'Outdated', biased: 'Biased',
      potentially_offensive: 'Potentially Offensive', factually_incorrect: 'Factually Incorrect',
    };
    const scoreColor = analysis.summary.score >= 90 ? '#22c55e'
      : analysis.summary.score >= 70 ? '#f59e0b'
      : analysis.summary.score >= 50 ? '#f97316' : '#ef4444';
    const issuesHTML = analysis.results.length === 0
      ? '<tr><td colspan="4" style="text-align:center;color:#6b7280">No issues found</td></tr>'
      : analysis.results.map(r => `
          <tr>
            <td><strong>${r.phrase}</strong></td>
            <td><span style="background:${severityColor[r.severity]}22;color:${severityColor[r.severity]};padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600">${severityLabel[r.severity]}</span></td>
            <td>${r.explanation}</td>
            <td style="color:#7b61ff">${r.suggestion || '—'}</td>
          </tr>`).join('');
    const wc = analysis.text.split(/\s+/).filter(Boolean).length;
    win.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8">
      <title>Inclusify — ${fileName}</title>
      <style>
        body{font-family:Arial,sans-serif;padding:40px;color:#1e293b;max-width:900px;margin:0 auto}
        h1{font-size:24px;color:#7b61ff;margin-bottom:4px}
        .meta{color:#64748b;font-size:13px;margin-bottom:24px}
        .score-row{display:flex;align-items:baseline;gap:8px;margin-bottom:8px}
        .score{font-size:52px;font-weight:800;color:${scoreColor};line-height:1}
        .score-label{font-size:14px;color:${scoreColor};font-weight:600}
        .stats{display:flex;gap:24px;margin-bottom:28px;padding:16px;background:#f8fafc;border-radius:8px}
        .stat-val{font-size:24px;font-weight:700;color:#1e293b}
        .stat-key{font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em}
        table{width:100%;border-collapse:collapse;font-size:13px}
        th{background:#f1f5f9;padding:10px 12px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#64748b;border-bottom:2px solid #e2e8f0}
        td{padding:10px 12px;border-bottom:1px solid #f1f5f9;vertical-align:top}
        tr:last-child td{border-bottom:none}
        @media print{body{padding:20px}}
      </style></head><body>
      <h1>INCLUSIFY — Analysis Report</h1>
      <div class="meta"><strong>File:</strong> ${fileName} &nbsp;|&nbsp; <strong>Date:</strong> ${new Date().toLocaleDateString()} &nbsp;|&nbsp; <strong>Mode:</strong> ${analysisMode || 'rules_only'}</div>
      <div class="score-row"><span class="score">${analysis.summary.score}</span><span style="font-size:20px;color:#94a3b8">/100</span><span class="score-label">${analysis.summary.score >= 90 ? 'Excellent' : analysis.summary.score >= 70 ? 'Good' : analysis.summary.score >= 50 ? 'Needs Improvement' : 'Requires Attention'}</span></div>
      <div class="stats">
        <div><div class="stat-val">${analysis.results.length}</div><div class="stat-key">Issues Found</div></div>
        <div><div class="stat-val">${wc.toLocaleString()}</div><div class="stat-key">Words</div></div>
        <div><div class="stat-val">${analysis.counts.potentially_offensive + analysis.counts.factually_incorrect}</div><div class="stat-key">High Severity</div></div>
        <div><div class="stat-val">${analysis.counts.outdated + analysis.counts.biased}</div><div class="stat-key">Low Severity</div></div>
      </div>
      <table><thead><tr><th>Flagged Term</th><th>Severity</th><th>Explanation</th><th>Suggestion</th></tr></thead>
      <tbody>${issuesHTML}</tbody></table>
      <script>window.onload=()=>window.print()<\/script>
    </body></html>`);
    win.document.close();
  }, [analysis, fileName, analysisMode]);

  // Keyboard navigation for issues list
  useKeyboardNavigation({
    containerRef: issuesListRef,
    itemSelector: 'button[role="listitem"]',
    enabled: viewState === 'results' && analysis.results.length > 0,
    onSelect: (_, index) => {
      if (analysis.results[index]) {
        handleIssueClick(analysis.results[index]);
      }
    },
  });

  // Render highlighted text with paragraph-aware layout and tooltips
  const renderHighlightedText = () => {
    const { text, annotations } = analysis;
    if (!text) return null;

    const parts: Array<{ content: string; annotation?: Annotation }> = [];
    let cursor = 0;

    const sorted = [...annotations].sort((a, b) => a.start - b.start);
    const nonOverlapping: Annotation[] = [];
    let lastEnd = -1;
    for (const ann of sorted) {
      if (ann.start >= lastEnd) { nonOverlapping.push(ann); lastEnd = ann.end; }
    }
    for (const ann of nonOverlapping) {
      if (ann.start > cursor) parts.push({ content: text.slice(cursor, ann.start) });
      parts.push({ content: text.slice(ann.start, ann.end), annotation: ann });
      cursor = ann.end;
    }
    if (cursor < text.length) parts.push({ content: text.slice(cursor) });

    // Split into paragraphs on \n\n; handle \n as <br> within paragraphs
    let key = 0;
    const paragraphs: React.ReactNode[][] = [[]];

    for (const part of parts) {
      if (part.annotation) {
        paragraphs[paragraphs.length - 1].push(
          <span key={key++} id={`ann-${part.annotation.start}`}>
            <IssueTooltip annotation={part.annotation}>
              {part.content}
            </IssueTooltip>
          </span>
        );
      } else {
        const blocks = part.content.split('\n\n');
        blocks.forEach((block, bi) => {
          if (bi > 0) paragraphs.push([]);
          const lines = block.split('\n');
          lines.forEach((line, li) => {
            if (li > 0) paragraphs[paragraphs.length - 1].push(<br key={key++} />);
            if (line) paragraphs[paragraphs.length - 1].push(<span key={key++}>{line}</span>);
          });
        });
      }
    }

    return (
      <div className="space-y-4">
        {paragraphs.filter(p => p.length > 0).map((para, i) => (
          <p key={i} className="leading-7 text-slate-700 dark:text-slate-200">
            {para}
          </p>
        ))}
      </div>
    );
  };

  const totalIssues = analysis.counts.outdated + analysis.counts.biased + analysis.counts.potentially_offensive + analysis.counts.factually_incorrect;
  const wordCount = analysis.text.split(/\s+/).filter(Boolean).length;
  const filteredResults = filterSeverity === 'all'
    ? analysis.results
    : analysis.results.filter(r => r.severity === filterSeverity);

  // Prepare translations for child components
  const uploadTranslations = {
    title: t('uploadTitle'),
    description: t('uploadDesc'),
    dragDrop: t('dragDrop'),
    dropHere: t('dropHere'),
    chooseDifferent: t('chooseDifferent'),
    analyzePaper: t('analyzePaper'),
    fileError: t('fileError'),
    fileSizeError: t('fileSizeError'),
  };

  const processingTranslations = {
    uploading: t('processing.uploading'),
    uploadingDesc: t('processing.uploadingDesc'),
    parsing: t('processing.parsing'),
    parsingDesc: t('processing.parsingDesc'),
    analyzing: t('processing.analyzing'),
    analyzingDesc: t('processing.analyzingDesc'),
    generating: t('processing.generating'),
    generatingDesc: t('processing.generatingDesc'),
    complete: t('processing.complete'),
    completeDesc: t('processing.completeDesc'),
  };

  const summaryTranslations = {
    score: t('summaryCard.score'),
    totalIssues: t('summaryCard.totalIssues'),
    wordCount: t('summaryCard.wordCount'),
    categories: t('summaryCard.categories'),
    recommendations: t('summaryCard.recommendations'),
    excellent: t('summaryCard.excellent'),
    good: t('summaryCard.good'),
    needsImprovement: t('summaryCard.needsImprovement'),
    requiresAttention: t('summaryCard.requiresAttention'),
    outdated: t('summaryCard.outdated'),
    biased: t('summaryCard.biased'),
    potentially_offensive: t('summaryCard.potentially_offensive'),
    factually_incorrect: t('summaryCard.factually_incorrect'),
    exportReport: t('exportReport'),
  };

  const features = [
    { icon: Scan, title: t('features.smartDetection'), desc: t('features.smartDetectionDesc') },
    { icon: BarChart3, title: t('features.detailedReports'), desc: t('features.detailedReportsDesc') },
    { icon: ShieldCheck, title: t('features.privacyFirst'), desc: t('features.privacyFirstDesc') },
  ];

  const BackIcon = isHebrew ? ChevronRight : ChevronLeft;

  return (
    <>
      {backendHealthy === false && (
        <HealthWarningBanner message={t('serviceUnavailable')} />
      )}
      {backendHealthy !== false && modelAvailable === false && (
        <HealthWarningBanner
          message={t('modelUnavailable')}
          variant="info"
        />
      )}
      <div className="flex flex-col flex-1">
        <AnimatePresence mode="wait">
          {/* Upload State */}
          {viewState === 'upload' && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="flex-1 flex flex-col justify-center max-w-4xl mx-auto w-full px-4 py-4"
            >
              {/* Header */}
              <div className="text-center mb-4">
                <motion.h1
                  className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-pride-purple to-pride-pink bg-clip-text text-transparent mb-2"
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                >
                  {t('uploadTitle')}
                </motion.h1>
                <motion.p
                  className="text-slate-500 dark:text-slate-400 max-w-md mx-auto text-sm"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.2 }}
                >
                  {t('uploadDesc')}
                </motion.p>
              </div>

              {/* Private Mode Toggle */}
              <div className="mb-4 flex justify-center">
                <PrivateModeToggle
                  checked={privateMode}
                  onCheckedChange={setPrivateMode}
                />
              </div>

              {/* Upload Component */}
              <PaperUpload
                onFileSelect={handleFileSelect}
                translations={uploadTranslations}
              />

              {/* Features */}
              <motion.div
                className="mt-4 grid grid-cols-3 gap-3"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                {features.map((feature, i) => {
                  const Icon = feature.icon;
                  return (
                    <div
                      key={i}
                      className="p-3 rounded-lg bg-slate-50/50 dark:bg-slate-800/30 border border-slate-100 dark:border-slate-800 text-center"
                    >
                      <div className="flex justify-center mb-1.5">
                        <Icon className="w-5 h-5 text-pride-purple" />
                      </div>
                      <h3 className="font-semibold text-xs text-slate-800 dark:text-white">{feature.title}</h3>
                      <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">{feature.desc}</p>
                    </div>
                  );
                })}
              </motion.div>

              {/* Error Message */}
              {errorMessage && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  dir={isHebrew ? 'rtl' : 'ltr'}
                  className="mt-4 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800"
                >
                  <p className="text-sm text-red-700 dark:text-red-400">{errorMessage}</p>
                </motion.div>
              )}
            </motion.div>
          )}

          {/* Processing State */}
          {viewState === 'processing' && (
            <motion.div
              key="processing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="flex-1 flex items-center justify-center px-4"
            >
              <ProcessingAnimation
                fileName={fileName}
                stage={processingStage}
                translations={processingTranslations}
              />
            </motion.div>
          )}

          {/* Results State */}
          {viewState === 'results' && (
            <motion.div
              key="results"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="h-[calc(100vh-130px)] flex flex-col py-3"
            >
              {/* Results Header */}
              <div className="flex flex-wrap items-center justify-between gap-4 mb-4 flex-shrink-0">
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleReset}
                    className="btn-ghost p-2 rounded-lg"
                    aria-label="Go back"
                  >
                    <BackIcon className="w-5 h-5" />
                  </button>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h2 className="font-semibold text-lg text-slate-800 dark:text-white flex items-center gap-2">
                        <FileText className="w-5 h-5 text-pride-purple" />
                        {fileName}
                      </h2>
                      {/* Inline score badge */}
                      <span className={cn(
                        'px-2 py-0.5 text-xs font-bold rounded-full border',
                        analysis.summary.score >= 90
                          ? 'bg-green-50 text-green-700 border-green-200 dark:bg-green-900/20 dark:text-green-400 dark:border-green-800'
                          : analysis.summary.score >= 70
                          ? 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800'
                          : analysis.summary.score >= 50
                          ? 'bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-900/20 dark:text-orange-400 dark:border-orange-800'
                          : 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800'
                      )}>
                        {analysis.summary.score}/100
                      </span>
                      {privateMode && (
                        <span className="flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-pride-purple/10 text-pride-purple border border-pride-purple/20">
                          <Lock className="w-3 h-3" />
                          {t('privateMode.badge')}
                        </span>
                      )}
                      {analysisMode === 'rules_only' && (
                        <span
                          className="px-2 py-0.5 text-xs rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                          title={t('basicAnalysisModeDesc')}
                        >
                          {t('basicAnalysisMode')}
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-500 mt-0.5">
                      {totalIssues} {totalIssues === 1 ? t('issueFound') : t('issuesFoundPlural')}
                      {' · '}
                      {wordCount.toLocaleString()} {t('summaryCard.wordCount').toLowerCase()}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={exportCSV}
                    className="btn-ghost px-3 py-2 rounded-lg text-sm flex items-center gap-1.5"
                    title="Export as CSV"
                  >
                    <Download className="w-4 h-4" />
                    CSV
                  </button>
                  <button
                    onClick={exportPDF}
                    className="btn-ghost px-3 py-2 rounded-lg text-sm flex items-center gap-1.5"
                    title="Export as PDF"
                  >
                    <FileText className="w-4 h-4" />
                    PDF
                  </button>
                  <div className="w-px h-5 bg-slate-200 dark:bg-slate-700" />
                  <button
                    onClick={handleReset}
                    className="btn-ghost px-4 py-2 rounded-lg text-sm flex items-center gap-2"
                  >
                    <RotateCcw className="w-4 h-4" />
                    {t('analyzeAnother')}
                  </button>
                </div>
              </div>

              {/* Main Content — always side-by-side: text LEFT, analysis RIGHT (RTL reverses naturally) */}
              <div className="flex-1 min-h-0 flex flex-row gap-4">
                {/* Text Panel — flexible width */}
                <div className="flex-1 min-w-0 min-h-0 glass rounded-xl border overflow-hidden flex flex-col">
                  <div className="px-4 py-3 border-b bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between flex-shrink-0">
                    <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                      {t('documentContent')}
                    </span>
                    <span className="text-xs text-slate-400">
                      {t('hoverHint')}
                    </span>
                  </div>
                  <div
                    className="flex-1 p-6 overflow-y-auto scroll-smooth min-h-0 text-[14.5px]"
                    dir={isHebrew ? 'rtl' : 'ltr'}
                  >
                    {renderHighlightedText()}
                  </div>
                  {/* Color legend — only when there are annotations */}
                  {analysis.annotations.length > 0 && (
                    <div className="px-4 py-2 border-t bg-slate-50/50 dark:bg-slate-800/50 flex flex-wrap gap-x-4 gap-y-1 flex-shrink-0">
                      {(['outdated', 'biased', 'potentially_offensive', 'factually_incorrect'] as const)
                        .filter(k => analysis.counts[k] > 0)
                        .map(k => {
                          const dotColor = k === 'outdated' ? 'bg-sky-400' : k === 'biased' ? 'bg-amber-400' : k === 'potentially_offensive' ? 'bg-rose-500' : 'bg-red-500';
                          const label = { outdated: t('summaryCard.outdated'), biased: t('summaryCard.biased'), potentially_offensive: t('summaryCard.potentially_offensive'), factually_incorrect: t('summaryCard.factually_incorrect') }[k];
                          const dimmed = filterSeverity !== 'all' && filterSeverity !== k;
                          return (
                            <button
                              key={k}
                              onClick={() => setFilterSeverity(filterSeverity === k ? 'all' : k)}
                              className="flex items-center gap-1.5"
                              title={label}
                            >
                              <div className={cn('w-2.5 h-2.5 rounded-sm flex-shrink-0 transition-opacity', dotColor, dimmed && 'opacity-30')} />
                              <span className={cn('text-xs transition-colors', dimmed ? 'text-slate-300 dark:text-slate-600' : 'text-slate-500 dark:text-slate-400')}>{label}</span>
                            </button>
                          );
                        })}
                    </div>
                  )}
                </div>

                {/* Analysis Panel — fixed width */}
                <div className="w-[520px] flex-shrink-0 min-h-0 flex flex-col gap-4 overflow-y-auto scroll-smooth pb-4">
                  {/* Summary Card */}
                  <AnalysisSummary
                    counts={analysis.counts}
                    score={analysis.summary.score}
                    recommendations={analysis.summary.recommendations}
                    wordCount={wordCount}
                    translations={summaryTranslations}
                  />

                  {/* Issues List */}
                  <div className="glass rounded-xl border overflow-hidden flex flex-col">
                    <div className="px-4 pt-3 pb-2 border-b bg-slate-50/50 dark:bg-slate-800/50 flex-shrink-0">
                      <h3 className="text-sm font-semibold flex items-center gap-2 mb-2">
                        {t('issuesFound')}
                        <span className="px-2 py-0.5 text-xs rounded-full bg-pride-purple/20 text-pride-purple">
                          {filteredResults.length !== analysis.results.length
                            ? `${filteredResults.length}/${analysis.results.length}`
                            : analysis.results.length}
                        </span>
                      </h3>
                      {/* Severity filter tabs — always visible when there are results */}
                      {analysis.results.length > 0 && (
                        <div className="flex gap-1.5 flex-wrap mt-1">
                          <button
                            onClick={() => setFilterSeverity('all')}
                            className={cn(
                              'px-2.5 py-1 text-xs rounded-full border font-medium transition-colors',
                              filterSeverity === 'all'
                                ? 'bg-pride-purple text-white border-transparent'
                                : 'text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:border-pride-purple/40'
                            )}
                          >
                            {t('filterAll')} ({totalIssues})
                          </button>
                          {(['potentially_offensive', 'factually_incorrect', 'biased', 'outdated'] as const)
                            .filter(k => analysis.counts[k] > 0)
                            .map(k => {
                              const label = {
                                outdated: t('summaryCard.outdated'),
                                biased: t('summaryCard.biased'),
                                potentially_offensive: t('summaryCard.potentially_offensive'),
                                factually_incorrect: t('summaryCard.factually_incorrect'),
                              }[k];
                              const dot = k === 'outdated' ? 'bg-sky-400' : k === 'biased' ? 'bg-amber-400' : k === 'potentially_offensive' ? 'bg-rose-500' : 'bg-red-500';
                              return (
                                <button
                                  key={k}
                                  onClick={() => setFilterSeverity(k)}
                                  className={cn(
                                    'px-2.5 py-1 text-xs rounded-full border font-medium transition-colors flex items-center gap-1.5',
                                    filterSeverity === k
                                      ? 'bg-pride-purple text-white border-transparent'
                                      : 'text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:border-pride-purple/40'
                                  )}
                                >
                                  <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', filterSeverity === k ? 'bg-white' : dot)} />
                                  {label} ({analysis.counts[k]})
                                </button>
                              );
                            })}
                        </div>
                      )}
                    </div>

                    <div
                      ref={issuesListRef}
                      className="divide-y divide-slate-100 dark:divide-slate-800"
                      role="list"
                      aria-label={t('a11y.issuesList')}
                    >
                      {analysis.results.length === 0 ? (
                        <div className="p-8 text-center">
                          <div className="text-4xl mb-3">🎉</div>
                          <p className="font-semibold text-green-600 dark:text-green-400 mb-1">{t('noIssuesFound')}</p>
                          <p className="text-sm text-slate-500 dark:text-slate-400">{t('noIssuesMessage')}</p>
                        </div>
                      ) : filteredResults.length === 0 ? (
                        <div className="p-6 text-center">
                          <p className="text-sm text-slate-500 dark:text-slate-400">{t('noIssuesInCategory')}</p>
                        </div>
                      ) : (
                        filteredResults.map((result, i) => (
                          <motion.button
                            key={result.phrase + i}
                            onClick={() => handleIssueClick(result)}
                            className="w-full text-start hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pride-purple focus-visible:ring-inset relative group"
                            role="listitem"
                            tabIndex={0}
                            initial={{ opacity: 0, x: isHebrew ? -20 : 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.04 }}
                          >
                            {/* Severity color strip */}
                            <div className={cn(
                              'absolute inset-y-0 w-1',
                              isHebrew ? 'right-0' : 'left-0',
                              result.severity === 'outdated' ? 'bg-sky-400'
                              : result.severity === 'biased' ? 'bg-amber-400'
                              : result.severity === 'potentially_offensive' ? 'bg-rose-500'
                              : 'bg-red-500'
                            )} />
                            <div className={cn('py-3 flex items-start gap-3', isHebrew ? 'pr-4 pl-3' : 'pl-4 pr-3')}>
                              <div className="flex-1 min-w-0">
                                <p className="font-semibold text-sm text-slate-800 dark:text-white mb-0.5 truncate">
                                  &ldquo;{result.phrase}&rdquo;
                                </p>
                                <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
                                  {result.explanation}
                                </p>
                                {result.suggestion && (
                                  <p className="text-xs text-pride-purple mt-1.5 flex items-center gap-1">
                                    <ArrowRight className="w-3 h-3 flex-shrink-0" />
                                    <span className="truncate">{result.suggestion}</span>
                                  </p>
                                )}
                              </div>
                              <div className="flex flex-col items-end gap-1.5 flex-shrink-0 mt-0.5">
                                <SeverityBadge level={result.severity} />
                                <ChevronRight className={cn(
                                  'w-3.5 h-3.5 text-slate-300 dark:text-slate-600 transition-transform group-hover:translate-x-0.5',
                                  isHebrew && 'rotate-180 group-hover:-translate-x-0.5 group-hover:translate-x-0'
                                )} />
                              </div>
                            </div>
                          </motion.button>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Guest Prompt */}
                  {!user && showGuestPrompt && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 }}
                      className="p-4 bg-gradient-to-r from-pride-purple/10 to-pride-blue/10 rounded-lg border border-pride-purple/20"
                    >
                      <p className="text-sm text-slate-700 dark:text-slate-300 mb-3">
                        {t('guestPrompt.title')}
                      </p>
                      <div className="flex gap-3">
                        <Link
                          href={`/${locale}/register`}
                          className="px-4 py-2 text-sm font-medium rounded-lg bg-pride-purple text-white hover:bg-pride-purple/90 transition-colors"
                        >
                          {t('guestPrompt.cta')}
                        </Link>
                        <button
                          onClick={() => setShowGuestPrompt(false)}
                          className="text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                        >
                          {t('guestPrompt.dismiss')}
                        </button>
                      </div>
                    </motion.div>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

    </>
  );
}
