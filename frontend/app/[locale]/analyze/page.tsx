'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import AnnotationSidePanel from '@/components/AnnotationSidePanel';
import PaperUpload from '@/components/PaperUpload';
import ProcessingAnimation from '@/components/ProcessingAnimation';
import HealthWarningBanner from '@/components/HealthWarningBanner';
import { Annotation } from '@/components/AnnotatedText';
import DocumentViewer, { PdfNavHandle } from '@/components/DocumentViewer';
import { analyzeText, uploadFile, healthCheck, modelHealthCheck, AnalysisCancelledError, BboxAnnotation, PageSize, AnalysisResult } from '@/lib/api/client';
import ConfirmDialog from '@/components/ConfirmDialog';
import { exportReport } from '@/lib/exportReport';
import { computeInclusivityScore } from '@/lib/score';
import { registerNavigationGuard } from '@/lib/navigationGuard';
import { useAuth } from '@/contexts/AuthContext';
import { useLiveAnnouncer } from '@/contexts/LiveAnnouncerContext';
import { useKeyboardNavigation } from '@/hooks/useKeyboardNavigation';
import {
  RotateCcw, FileText, ChevronLeft, ChevronRight, Scan, BarChart3, ShieldCheck,
  Lock, Mail, Download, AlertCircle, CheckCircle2, Filter, Type,
} from 'lucide-react';
import PrivateModeToggle from '@/components/PrivateModeToggle';
import ContactModal from '@/components/ContactModal';
import { cn } from '@/lib/utils';

type Severity = 'outdated' | 'biased' | 'potentially_offensive' | 'factually_incorrect';
type ViewState = 'upload' | 'processing' | 'results';

interface AnalysisData {
  text: string;
  annotations: Annotation[];
  results: Array<{
    phrase: string;
    severity: Severity;
    category?: string;
    explanation: string;
    suggestion?: string;
    references?: Array<{ label: string; url: string }>;
  }>;
  counts: Record<Severity, number>;
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

function getScoreColor(score: number): string {
  if (score >= 90) return 'text-green-500';
  if (score >= 70) return 'text-amber-500';
  if (score >= 50) return 'text-orange-500';
  return 'text-red-500';
}

export default function AnalyzePage() {
  const t = useTranslations('analyzer');
  const locale = useLocale();
  const isHebrew = locale === 'he';
  const { user } = useAuth();
  const { announce } = useLiveAnnouncer();
  const issuesListRef = useRef<HTMLDivElement>(null);
  const textPanelRef = useRef<HTMLDivElement>(null);

  const router = useRouter();
  const [viewState, setViewState] = useState<ViewState>('upload');
  const [fileName, setFileName] = useState('');
  const [inputMode, setInputMode] = useState<'upload' | 'paste'>('upload');
  const [pastedText, setPastedText] = useState('');
  // Navigation guard: where the user tried to go while analysis was running —
  // either an intercepted link (href) or a programmatic navigation (proceed),
  // e.g. the language switcher.
  const [pendingNav, setPendingNav] = useState<{ href?: string; proceed?: () => void; source: 'processing' | 'results' } | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const cancelledRef = useRef(false);
  const [analysis, setAnalysis] = useState<AnalysisData>(emptyAnalysis);
  const [activeFilters, setActiveFilters] = useState<Set<Severity>>(new Set());
  const [activeTypeFilters, setActiveTypeFilters] = useState<Set<string>>(new Set());
  const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);
  const [selectedResultIndex, setSelectedResultIndex] = useState<number | null>(null);
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [modelAvailable, setModelAvailable] = useState<boolean | null>(null);
  const [analysisMode, setAnalysisMode] = useState<'llm' | null>(null);
  const [currentRunId, setCurrentRunId] = useState<string | undefined>();
  const [showGuestPrompt, setShowGuestPrompt] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [processingStage, setProcessingStage] = useState<'uploading' | 'parsing' | 'analyzing' | 'generating' | 'complete'>('uploading');
  const [privateMode, setPrivateMode] = useState(false);
  const [contactOpen, setContactOpen] = useState(false);
  // Document viewer state
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [docInputType, setDocInputType] = useState<'pdf' | 'docx' | 'pptx' | 'txt'>('txt');
  const [bboxAnnotations, setBboxAnnotations] = useState<BboxAnnotation[] | null>(null);
  const [pageSizes, setPageSizes] = useState<Record<string, PageSize> | null>(null);
  const [markdownText, setMarkdownText] = useState<string | null>(null);
  const pdfViewerRef = useRef<PdfNavHandle | null>(null);
  const [pdfNumPages, setPdfNumPages] = useState(0);
  const [pdfCurrentPage, setPdfCurrentPage] = useState(1);
  const [pdfSearchTerm, setPdfSearchTerm] = useState('');

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

  const handleApiError = useCallback((error: unknown) => {
    let message = t('errors.generic');
    if (error instanceof Error) {
      const errorText = error.message.toLowerCase();
      if (errorText.includes('password-protected') || errorText.includes('password')) {
        message = t('errors.passwordProtected');
      } else if (errorText.includes('scanned') || errorText.includes('no extractable text')) {
        message = t('errors.scannedPdf');
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

  // Shared post-analysis step: compute score + recommendations and switch to results
  const finishAnalysis = useCallback((text: string, result: AnalysisResult) => {
    const wc = text.split(/\s+/).filter(Boolean).length;
    const score = computeInclusivityScore(result.counts, wc);

    const recommendations: string[] = [];
    if (result.counts.potentially_offensive > 0) recommendations.push(t('recommendations.potentially_offensive'));
    if (result.counts.factually_incorrect > 0) recommendations.push(t('recommendations.factually_incorrect'));
    if (result.counts.biased > 0) recommendations.push(t('recommendations.biased'));
    if (result.counts.outdated > 0) recommendations.push(t('recommendations.outdated'));
    if (recommendations.length === 0) recommendations.push(t('recommendations.excellent'));

    setAnalysis({
      text,
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
    setCurrentRunId(result.runId);
    setViewState('results');
    announce(t('a11y.analysisComplete', { count: Object.values(result.counts).reduce((a, b) => a + b, 0) }));
  }, [t, announce]);

  const handleFileSelect = useCallback(async (file: File) => {
    setErrorMessage(null);
    setFileName(file.name);
    setViewState('processing');
    announce(t('a11y.uploadStarted'));

    cancelledRef.current = false;
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      setProcessingStage('uploading');
      const uploadResult = await uploadFile(file, controller.signal, privateMode);
      setProcessingStage('analyzing');

      const result = await analyzeText(uploadResult.text, {
        language: locale as 'en' | 'he' | 'auto',
        privateMode,
        useAuth: true,
        signal: controller.signal,
        fileMeta: {
          filename: uploadResult.filename,
          mimeType: uploadResult.mimeType,
          inputType: uploadResult.inputType,
          pageCount: uploadResult.pageCount,
          title: uploadResult.title,
          author: uploadResult.author,
          detectedLanguage: uploadResult.detectedLanguage,
          fileStorageRef: uploadResult.fileStorageRef,
          chunks: uploadResult.chunks,
        },
      });

      setProcessingStage('complete');

      // Store document viewer metadata
      setUploadedFile(file);
      setDocInputType(uploadResult.inputType);
      setBboxAnnotations(uploadResult.bboxAnnotations ?? null);
      setPageSizes(uploadResult.pageSizes ?? null);
      setMarkdownText(uploadResult.markdownText ?? null);
      finishAnalysis(uploadResult.text, result);
    } catch (error) {
      if (error instanceof AnalysisCancelledError || cancelledRef.current) return;
      console.error('Analysis failed:', error);
      handleApiError(error);
    }
  }, [locale, t, handleApiError, privateMode, announce, finishAnalysis]);

  // Direct text input: feeds the same analysis pipeline but skips the
  // upload/extraction step entirely — the raw text goes straight to /analyze.
  const handleAnalyzeRawText = useCallback(async () => {
    const text = pastedText.trim();
    if (text.length < 20) {
      setErrorMessage(t('textTooShort'));
      return;
    }
    setErrorMessage(null);
    setFileName(t('pastedTextName'));
    setViewState('processing');
    setProcessingStage('analyzing');
    announce(t('a11y.uploadStarted'));

    cancelledRef.current = false;
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const result = await analyzeText(text, {
        language: locale as 'en' | 'he' | 'auto',
        privateMode,
        useAuth: true,
        signal: controller.signal,
      });

      setProcessingStage('complete');

      // Plain-text viewer: no file, no PDF overlays
      setUploadedFile(null);
      setDocInputType('txt');
      setBboxAnnotations(null);
      setPageSizes(null);
      setMarkdownText(null);
      finishAnalysis(text, result);
    } catch (error) {
      if (error instanceof AnalysisCancelledError || cancelledRef.current) return;
      console.error('Analysis failed:', error);
      handleApiError(error);
    }
  }, [pastedText, locale, t, handleApiError, privateMode, announce, finishAnalysis]);

  // Guard in-app navigation during analysis (processing) and after results are shown.
  // During processing: also block tab/window close via beforeunload.
  // During results: only intercept in-app link clicks and programmatic navigation
  // (e.g. the language switcher) so we can confirm before wiping the results.
  useEffect(() => {
    if (viewState !== 'processing' && viewState !== 'results') return;
    const source = viewState as 'processing' | 'results';

    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = '';
    };
    const handleClickCapture = (e: MouseEvent) => {
      const anchor = (e.target as HTMLElement).closest?.('a[href]') as HTMLAnchorElement | null;
      if (!anchor) return;
      const href = anchor.getAttribute('href');
      if (!href || href.startsWith('#')) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey || anchor.target === '_blank') return;
      e.preventDefault();
      e.stopPropagation();
      setPendingNav({ href, source });
    };

    if (source === 'processing') window.addEventListener('beforeunload', handleBeforeUnload);
    document.addEventListener('click', handleClickCapture, true);
    // Programmatic navigation (router.push/replace from buttons, e.g. the
    // language switcher) bypasses the click capture — guard it too.
    const unregister = registerNavigationGuard((proceed) => setPendingNav({ proceed, source }));
    return () => {
      if (source === 'processing') window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('click', handleClickCapture, true);
      unregister();
    };
  }, [viewState]);

  const handleReset = useCallback(() => {
    setViewState('upload');
    setFileName('');
    setPastedText('');
    setAnalysis(emptyAnalysis);
    setSelectedAnnotation(null);
    setSelectedResultIndex(null);
    setSidePanelOpen(false);
    setAnalysisMode(null);
    setErrorMessage(null);
    setProcessingStage('uploading');
    setShowGuestPrompt(true);
    setPrivateMode(false);
    setUploadedFile(null);
    setBboxAnnotations(null);
    setPageSizes(null);
    setMarkdownText(null);
  }, []);

  // User confirmed leaving: abort the in-flight request if still processing,
  // then reset state and navigate.
  const confirmLeave = useCallback(() => {
    const target = pendingNav;
    if (target?.source === 'processing') {
      cancelledRef.current = true;
      abortRef.current?.abort();
    }
    setPendingNav(null);
    handleReset();
    if (target?.href) router.push(target.href);
    else target?.proceed?.();
  }, [pendingNav, handleReset, router]);

  // Shared normalizer: NFC + case-fold + collapse all Unicode whitespace variants.
  // Ensures Hebrew phrases (no case) and phrases with NBSP/directional marks still match.
  const normStr = useCallback((s: string) =>
    s.normalize('NFC').toLowerCase()
     .replace(/[\s ​‌‍‎‏﻿]+/g, ' ')
     .trim()
  , []);

  const handleIssueClick = useCallback((result: AnalysisData['results'][0], index: number) => {
    const normPhrase = normStr(result.phrase);
    // Use index directly — analysis.annotations[i] is the 1:1 match for analysis.results[i].
    // This correctly handles duplicate phrases where phrase-only lookup would always find the first.
    const annotation =
      analysis.annotations[index] ??
      analysis.annotations.find((a) => normStr(a.label) === normPhrase) ??
      analysis.annotations.find(
        (a) =>
          normStr(a.label).includes(normPhrase) ||
          normPhrase.includes(normStr(a.label)),
      );

    setSelectedResultIndex(index);
    if (!annotation) return;

    const el = document.getElementById(`ann-${annotation.start}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.style.transition = 'box-shadow 0.3s';
      el.style.boxShadow = '0 0 0 3px rgba(124,58,237,0.6)';
      el.style.borderRadius = '4px';
      setTimeout(() => { el.style.boxShadow = ''; el.style.borderRadius = ''; }, 1500);
    } else if (docInputType === 'pdf') {
      const found = pdfViewerRef.current?.handleSearch(annotation.label);
      const found2 = !found && normStr(result.phrase) !== normStr(annotation.label)
        ? pdfViewerRef.current?.handleSearch(result.phrase)
        : found;
      // Last resort: estimate the page from the character-offset ratio and scroll there.
      // Catches phrases on pages whose text layers haven't been processed yet.
      if (!found2 && pdfNumPages > 0 && analysis.text.length > 0) {
        const estimatedPage = Math.max(1, Math.ceil(
          (annotation.start / analysis.text.length) * pdfNumPages,
        ));
        pdfViewerRef.current?.scrollToPage(estimatedPage);
      }
    }
  }, [analysis.annotations, analysis.text, docInputType, pdfNumPages, normStr]);

  const handleAnnotationClick = useCallback((annotation: Annotation) => {
    setSelectedAnnotation(annotation);
    setSidePanelOpen(true);
    const normLabel = normStr(annotation.label);
    // Exact match first — when multiple results share the same sentence, includes
    // would match the wrong (longer) result before the right (exact) one.
    let idx = analysis.results.findIndex((r) => normStr(r.phrase) === normLabel);
    if (idx === -1) {
      idx = analysis.results.findIndex(
        (r) => normStr(r.phrase).includes(normLabel) || normLabel.includes(normStr(r.phrase)),
      );
    }
    if (idx !== -1) {
      setSelectedResultIndex(idx);
      // Scroll the matching issue card into view in the right panel.
      requestAnimationFrame(() => {
        const card = document.querySelector(`[data-result-idx="${idx}"]`);
        card?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    }
  }, [analysis.results, normStr]);

  // Called when the user clicks/pins an annotation in the document viewer.
  // Scrolls the matching finding card into view WITHOUT opening the side panel overlay.
  const handleAnnotationPin = useCallback((annotation: Annotation) => {
    // Match by start offset + label — correctly handles duplicate phrases that share
    // the same text but appear at different positions in the document.
    let idx = analysis.annotations.findIndex(
      (a) => a.start === annotation.start && normStr(a.label) === normStr(annotation.label),
    );
    if (idx === -1) {
      // Fallback: phrase-only match (covers cases where start offsets differ slightly)
      const normLabel = normStr(annotation.label);
      idx = analysis.annotations.findIndex((a) => normStr(a.label) === normLabel);
    }
    if (idx !== -1) {
      setSelectedResultIndex(idx);
      requestAnimationFrame(() => {
        const card = document.querySelector(`[data-result-idx="${idx}"]`);
        card?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    }
  }, [analysis.annotations, normStr]);

  const toggleFilter = useCallback((sev: Severity) => {
    setActiveFilters(prev => {
      const next = new Set(prev);
      if (next.has(sev)) next.delete(sev); else next.add(sev);
      return next;
    });
  }, []);

  const toggleTypeFilter = useCallback((cat: string) => {
    setActiveTypeFilters(prev => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat); else next.add(cat);
      return next;
    });
  }, []);

  useKeyboardNavigation({
    containerRef: issuesListRef,
    itemSelector: 'button[role="listitem"]',
    enabled: viewState === 'results' && analysis.results.length > 0,
    onSelect: (_, index) => {
      if (analysis.results[index]) handleIssueClick(analysis.results[index], index);
    },
  });

  const wordCount = analysis.text.split(/\s+/).filter(Boolean).length;
  const categoryConfig = {
    outdated: {
      label: t('summaryCard.outdated'),
      bar: 'bg-sky-500',
      dot: 'bg-sky-400',
      text: 'text-sky-600 dark:text-sky-400',
    },
    biased: {
      label: t('summaryCard.biased'),
      bar: 'bg-amber-500',
      dot: 'bg-amber-400',
      text: 'text-amber-600 dark:text-amber-400',
    },
    potentially_offensive: {
      label: t('summaryCard.potentially_offensive'),
      bar: 'bg-orange-500',
      dot: 'bg-orange-400',
      text: 'text-orange-600 dark:text-orange-400',
    },
    factually_incorrect: {
      label: t('summaryCard.factually_incorrect'),
      bar: 'bg-red-500',
      dot: 'bg-red-400',
      text: 'text-red-600 dark:text-red-400',
    },
  } as const;

  const llmCategoryConfig: Record<string, { label: string; pill: string }> = {
    'Medicalization':       { label: t('llmCategoryMedicalization'),      pill: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300' },
    'Generalization':       { label: t('llmCategoryGeneralization'),       pill: 'bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300' },
    'Demeaning Terminology':{ label: t('llmCategoryDemeaning'),            pill: 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300' },
  };

  const severityBorderColor: Record<Severity, string> = {
    outdated: '#0ea5e9',
    biased: '#f59e0b',
    potentially_offensive: '#f97316',
    factually_incorrect: '#ef4444',
  };

  const severityOrder: Record<Severity, number> = {
    factually_incorrect: 0,
    potentially_offensive: 1,
    biased: 2,
    outdated: 3,
  };
  const severityPriority: Severity[] = ['factually_incorrect', 'potentially_offensive', 'biased', 'outdated'];

  const getResultConfidence = (result: AnalysisData['results'][0]) => {
    const np = normStr(result.phrase);
    return (
      analysis.annotations.find((a) => normStr(a.label) === np) ??
      analysis.annotations.find(
        (a) => normStr(a.label).includes(np) || np.includes(normStr(a.label)),
      )
    )?.confidence;
  };

  const confidenceFiltered = analysis.results.filter(r => {
    const conf = getResultConfidence(r);
    if (conf == null) return true;
    return conf >= 0.30 && conf <= 0.85;
  });

  const filteredCounts: Record<Severity, number> = {
    outdated: 0, biased: 0, potentially_offensive: 0, factually_incorrect: 0,
  };
  for (const r of confidenceFiltered) filteredCounts[r.severity]++;

  const totalIssues =
    filteredCounts.outdated +
    filteredCounts.biased +
    filteredCounts.potentially_offensive +
    filteredCounts.factually_incorrect;

  const filteredResults = confidenceFiltered
    .filter(r => activeFilters.size === 0 || activeFilters.has(r.severity))
    .filter(r => activeTypeFilters.size === 0 || (r.category != null && activeTypeFilters.has(r.category)))
    .sort((a, b) => severityOrder[a.severity] - severityOrder[b.severity]);

  // Only show highlights in the document viewer for phrases that passed confidence filtering
  const visiblePhrases = new Set(confidenceFiltered.map(r => r.phrase.toLowerCase()));
  const visibleAnnotations = analysis.annotations.filter(ann =>
    visiblePhrases.has(ann.label.toLowerCase()),
  );

  const handleExport = () => {
    exportReport(analysis, {
      fileName,
      locale,
      filteredResults,
      visibleAnnotations,
      displayScore: score,
      displayCounts: filteredCounts,
      recommendations: analysis.summary.recommendations,
    });
  };

  // Recompute score from confidence-filtered counts so it's consistent with the displayed findings.
  const score = computeInclusivityScore(filteredCounts, wordCount);

  const scoreLabel =
    score >= 90
      ? t('summaryCard.excellent')
      : score >= 70
      ? t('summaryCard.good')
      : score >= 50
      ? t('summaryCard.needsImprovement')
      : t('summaryCard.requiresAttention');

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
          linkHref={`/${locale}/glossary`}
          linkText={t('modelUnavailableLinkText')}
        />
      )}


      <div className="flex flex-col flex-1">
        <AnimatePresence mode="wait">

          {/* ── Upload ─────────────────────────────────────────────── */}
          {viewState === 'upload' && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="flex-1 flex flex-col justify-center max-w-4xl mx-auto w-full px-4 py-4"
            >
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

              <div className="mb-4 flex justify-center">
                <PrivateModeToggle checked={privateMode} onCheckedChange={setPrivateMode} />
              </div>

              {/* Input mode: upload a document or paste raw text */}
              <div className="mb-4 flex justify-center">
                <div
                  className="inline-flex rounded-xl border border-slate-200 dark:border-slate-700 p-1 bg-white/60 dark:bg-slate-900/60"
                  role="tablist"
                  aria-label={t('uploadTitle')}
                >
                  <button
                    role="tab"
                    aria-selected={inputMode === 'upload'}
                    onClick={() => setInputMode('upload')}
                    className={cn(
                      'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                      inputMode === 'upload'
                        ? 'bg-pride-purple text-white shadow-sm'
                        : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200',
                    )}
                  >
                    <FileText className="w-4 h-4" />
                    {t('inputTabUpload')}
                  </button>
                  <button
                    role="tab"
                    aria-selected={inputMode === 'paste'}
                    onClick={() => setInputMode('paste')}
                    className={cn(
                      'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                      inputMode === 'paste'
                        ? 'bg-pride-purple text-white shadow-sm'
                        : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200',
                    )}
                  >
                    <Type className="w-4 h-4" />
                    {t('inputTabPaste')}
                  </button>
                </div>
              </div>

              {inputMode === 'upload' ? (
                <PaperUpload onFileSelect={handleFileSelect} translations={uploadTranslations} />
              ) : (
                <div className="w-full max-w-4xl mx-auto">
                  <div className="rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-gradient-to-br from-slate-50/80 to-white/60 dark:from-slate-900/80 dark:to-slate-800/60 p-4 sm:p-6">
                    <h3 className="text-base font-semibold text-slate-800 dark:text-white mb-1">
                      {t('pasteTitle')}
                    </h3>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">
                      {t('pasteDesc')}
                    </p>
                    <textarea
                      value={pastedText}
                      onChange={(e) => setPastedText(e.target.value)}
                      rows={10}
                      // dir="auto" falls back to LTR while empty, rendering the
                      // Hebrew placeholder wrong — follow the locale until there
                      // is content, then let the content decide.
                      dir={pastedText.trim() ? 'auto' : isHebrew ? 'rtl' : 'ltr'}
                      placeholder={t('placeholder')}
                      className="w-full resize-y rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 text-sm text-slate-700 dark:text-slate-200 focus:outline-none focus:border-pride-purple focus:ring-2 focus:ring-pride-purple/20 placeholder:text-slate-300 dark:placeholder:text-slate-600"
                      aria-label={t('pasteTitle')}
                    />
                    {/* rtl:flex-row-reverse keeps the analyze button on the right in Hebrew */}
                    <div className="flex items-center justify-between mt-3 rtl:flex-row-reverse">
                      <span className="text-xs text-slate-400 tabular-nums">
                        {t('summaryCard.wordCount')}
                        {': '}
                        {pastedText.trim() ? pastedText.trim().split(/\s+/).filter(Boolean).length.toLocaleString() : 0}
                      </span>
                      <motion.button
                        onClick={handleAnalyzeRawText}
                        disabled={pastedText.trim().length < 20}
                        className="btn-primary py-3 px-6 disabled:opacity-50 disabled:cursor-not-allowed"
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                      >
                        {t('analyzeBtn')}
                      </motion.button>
                    </div>
                  </div>
                </div>
              )}

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

          {/* ── Processing ─────────────────────────────────────────── */}
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

          {/* ── Results ────────────────────────────────────────────── */}
          {viewState === 'results' && (
            <motion.div
              key="results"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="h-[calc(100vh-140px)] flex flex-col py-4"
            >
              {/* Header row */}
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4 flex-shrink-0">
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleReset}
                    className="btn-ghost p-2 rounded-lg"
                    aria-label="Go back"
                  >
                    <BackIcon className="w-5 h-5" />
                  </button>
                  <div>
                    <h2 className="font-semibold text-base text-slate-800 dark:text-white flex items-center gap-2 flex-wrap">
                      <FileText className="w-4 h-4 text-pride-purple flex-shrink-0" />
                      <span className="truncate max-w-[260px]">{fileName}</span>
                      {privateMode && (
                        <span className="flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-pride-purple/10 text-pride-purple">
                          <Lock className="w-3 h-3" />
                          {t('privateMode.badge')}
                        </span>
                      )}

                    </h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {totalIssues} {totalIssues === 1 ? t('issueFound') : t('issuesFoundPlural')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <motion.button
                    onClick={handleExport}
                    className="btn-ghost px-3 py-2 rounded-lg text-sm flex items-center gap-2 hover:border-pride-purple/40 hover:bg-pride-purple/5"
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                  >
                    <Download className="w-4 h-4" />
                    <span className="font-medium hidden sm:inline">{t('exportReport')}</span>
                  </motion.button>
                  <motion.button
                    onClick={() => setContactOpen(true)}
                    className="btn-ghost px-3 py-2 rounded-lg text-sm flex items-center gap-2 hover:border-pride-purple/40 hover:bg-pride-purple/5"
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                  >
                    <Mail className="w-4 h-4" />
                    <span className="font-medium hidden sm:inline">{t('contactUs')}</span>
                  </motion.button>
                  <button
                    onClick={handleReset}
                    className="btn-ghost px-3 py-2 rounded-lg text-sm flex items-center gap-2"
                  >
                    <RotateCcw className="w-4 h-4" />
                    <span className="hidden sm:inline">{t('analyzeAnother')}</span>
                  </button>
                </div>
              </div>

              {/* Two-column layout. Document is always the visual-RIGHT panel,
                   Findings always the visual-LEFT panel (fixed 520 px).
                   In RTL the CSS flex row already places Document on the right;
                   in LTR we use row-reverse so the visual order is the same. */}
              <div
                className="flex-1 min-h-0 flex gap-4"
                style={{ flexDirection: isHebrew ? 'row' : 'row-reverse' }}
              >
                {/* ── Document Viewer — always visual RIGHT ───────── */}
                <div className="glass rounded-xl border border-l-[3px] border-l-pride-purple overflow-hidden flex flex-col min-h-0 max-h-full flex-1 min-w-0">
                  {/* Panel header */}
                  <div className="px-4 py-3 border-b bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between flex-shrink-0">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-pride-purple" />
                      <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                        {t('documentPanel')}
                      </span>
                    </div>
                    <span className="text-xs text-slate-400">{t('hoverHint')}</span>
                  </div>

                  {/* Scrollable document area */}
                  <div
                    ref={textPanelRef}
                    className="flex-1 px-7 py-6 overflow-y-auto text-[0.9rem] text-slate-700 dark:text-slate-200 scroll-smooth min-h-0"
                    dir={isHebrew ? 'rtl' : 'ltr'}
                  >
                    <DocumentViewer
                      ref={pdfViewerRef}
                      inputType={docInputType}
                      text={analysis.text}
                      annotations={visibleAnnotations}
                      uploadedFile={uploadedFile}
                      bboxAnnotations={bboxAnnotations}
                      pageSizes={pageSizes}
                      markdownText={markdownText}
                      onAnnotationClick={handleAnnotationClick}
                      onAnnotationPin={handleAnnotationPin}
                      isHebrew={isHebrew}
                      onPdfNumPages={setPdfNumPages}
                      onPdfPageChange={setPdfCurrentPage}
                    />
                  </div>

                  {/* PDF nav bar */}
                  {docInputType === 'pdf' && pdfNumPages > 0 && (
                    <div className="px-3 py-1.5 border-t border-slate-200 dark:border-slate-700 bg-white/95 dark:bg-slate-900/95 flex items-center gap-2 text-xs flex-shrink-0">
                      <button onClick={() => pdfViewerRef.current?.scrollToPage(Math.max(1, pdfCurrentPage - 1))} disabled={pdfCurrentPage <= 1} className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors">
                        <ChevronLeft className="w-3.5 h-3.5" />
                      </button>
                      <span className="text-slate-500 dark:text-slate-400 tabular-nums">
                        Page {pdfCurrentPage} of {pdfNumPages}
                      </span>
                      <button onClick={() => pdfViewerRef.current?.scrollToPage(Math.min(pdfNumPages, pdfCurrentPage + 1))} disabled={pdfCurrentPage >= pdfNumPages} className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors">
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                      <div className="w-px h-4 bg-slate-200 dark:bg-slate-700 flex-shrink-0" />
                      <div className="flex items-center gap-1.5 flex-1 min-w-0">
                        <Download className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 hidden" />
                        <input
                          type="text"
                          placeholder="Search in document…"
                          value={pdfSearchTerm}
                          onChange={(e) => setPdfSearchTerm(e.target.value)}
                          onKeyDown={(e) => { if (e.key === 'Enter') pdfViewerRef.current?.handleSearch(pdfSearchTerm); }}
                          className="flex-1 min-w-0 text-xs px-2 py-0.5 rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:border-pride-purple placeholder:text-slate-300 dark:placeholder:text-slate-600"
                        />
                      </div>
                    </div>
                  )}

                  {/* Severity legend */}
                  <div className="px-4 py-2.5 border-t bg-slate-50/30 dark:bg-slate-800/30 flex flex-wrap gap-x-5 gap-y-1 flex-shrink-0">
                    {(Object.keys(categoryConfig) as Severity[]).map((sev) => (
                      <div key={sev} className="flex items-center gap-1.5">
                        <span className={cn('w-2.5 h-2.5 rounded-full flex-shrink-0', categoryConfig[sev].dot)} />
                        <span className="text-[11px] text-slate-500 dark:text-slate-400 whitespace-nowrap">
                          {categoryConfig[sev].label}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* ── Findings Panel — always visual LEFT ─────────── */}
                <div
                  className="flex flex-col gap-2 min-h-0 max-h-full overflow-y-auto pb-4 border-l-[3px] border-l-pride-purple pl-2 flex-shrink-0"
                  style={{ scrollBehavior: 'smooth', width: '520px' }}
                >
                  <div className="flex-shrink-0 pt-0.5 flex items-center justify-between">
                    <span className="text-[11px] font-bold text-pride-purple uppercase tracking-widest">
                      {t('findingsPanel')}
                    </span>
                  </div>
                  {/* Score Card */}
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                    className="glass rounded-lg border shadow-sm px-4 py-3.5 flex-shrink-0"
                  >
                    <div>
                      <p className="text-[10px] uppercase text-slate-400 mb-2 font-semibold">
                        {t('summaryCard.score')}
                      </p>

                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex items-baseline gap-2">
                            <motion.span
                              className={cn('text-5xl font-black tabular-nums leading-none', getScoreColor(score))}
                              initial={{ scale: 0.6, opacity: 0 }}
                              animate={{ scale: 1, opacity: 1 }}
                              transition={{ type: 'spring', stiffness: 180, damping: 14, delay: 0.1 }}
                            >
                              {score}
                            </motion.span>
                            <span className="text-slate-400 text-lg">/100</span>
                          </div>
                          <div className="flex items-center gap-1.5 mt-1.5">
                            {score >= 70 ? (
                              <CheckCircle2 className={cn('w-4 h-4', getScoreColor(score))} />
                            ) : (
                              <AlertCircle className={cn('w-4 h-4', getScoreColor(score))} />
                            )}
                            <span className={cn('text-sm font-semibold', getScoreColor(score))}>
                              {scoreLabel}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1.5 leading-relaxed">
                            {totalIssues} {t('scoreSummaryReview')}
                          </p>
                        </div>

                        <div className="flex flex-col gap-2 w-40 flex-shrink-0 border-l border-slate-200/70 dark:border-slate-700/70 pl-3">
                          <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 px-2.5 py-2 min-h-[50px] flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-lg bg-pride-purple/10 flex items-center justify-center flex-shrink-0">
                              <FileText className="w-4 h-4 text-pride-purple" />
                            </div>
                            <div className="min-w-0">
                              <p className="text-2xl font-black text-slate-900 dark:text-white tabular-nums leading-none tracking-tight">
                                {totalIssues}
                              </p>
                              <p className="text-[10px] text-slate-400 mt-0.5 leading-none whitespace-nowrap">
                                {t('summaryCard.totalIssues')}
                              </p>
                            </div>
                          </div>
                          <div className="rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 px-2.5 py-2 min-h-[50px] flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-lg bg-pride-purple/10 flex items-center justify-center flex-shrink-0">
                              <span className="text-xs font-bold text-pride-purple">Aa</span>
                            </div>
                            <div className="min-w-0">
                              <p className="text-xl font-black text-slate-900 dark:text-white tabular-nums leading-none tracking-tight">
                                {wordCount.toLocaleString()}
                              </p>
                              <p className="text-[10px] text-slate-400 mt-0.5 leading-none whitespace-nowrap">
                                {t('summaryCard.wordCount')}
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </motion.div>

                  {/* Category breakdown */}
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.08 }}
                    className="glass rounded-lg border shadow-sm p-4 flex-shrink-0"
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <BarChart3 className="w-4 h-4 text-pride-purple" />
                      <h3 className="text-sm font-semibold">{t('summaryCard.categories')}</h3>
                    </div>
                    <div className="space-y-2.5">
                      {severityPriority.map((sev) => {
                        const cfg = categoryConfig[sev];
                        const count = filteredCounts[sev];
                        const sharePct = totalIssues > 0 ? Math.round((count / totalIssues) * 100) : 0;
                        const barPct = sharePct;
                        return (
                          <div key={sev}>
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className={cn('font-medium', cfg.text)}>{cfg.label}</span>
                              <span className="font-bold text-slate-600 dark:text-slate-300 tabular-nums">
                                {count} · {sharePct}%
                              </span>
                            </div>
                            <div className="h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                              <motion.div
                                className={cn('h-full rounded-full', cfg.bar)}
                                initial={{ width: 0 }}
                                animate={{ width: `${barPct}%` }}
                                transition={{ duration: 0.6, delay: 0.15 }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </motion.div>

                  {/* Filter controls */}
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.12 }}
                    className="glass rounded-lg border shadow-sm p-4 flex-shrink-0"
                  >
                    <h3 className="text-sm font-semibold flex items-center gap-1.5 mb-3">
                      <Filter className="w-3.5 h-3.5 text-pride-purple" />
                      {t('filterFindings')}
                    </h3>

                    <div className="space-y-2.5">
                      {/* Severity row */}
                      <div className="space-y-1.5 min-w-0">
                        <span className="block text-[11px] text-slate-400">
                          {t('filterSeverity')}
                        </span>
                        <div className="flex flex-nowrap gap-1 overflow-x-auto pb-0.5">
                          <button
                            onClick={() => setActiveFilters(new Set())}
                            className={cn(
                              'h-7 px-2 rounded-lg text-[10px] font-semibold leading-none whitespace-nowrap border transition-all',
                              activeFilters.size === 0
                                ? 'bg-pride-purple text-white border-pride-purple'
                                : 'bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:border-pride-purple/40',
                            )}
                          >
                            {t('filterAll')} {confidenceFiltered.length}
                          </button>
                          {severityPriority.map((sev) => {
                            const cfg = categoryConfig[sev];
                            const active = activeFilters.has(sev);
                            const count = filteredCounts[sev];
                            return (
                              <button
                                key={sev}
                                onClick={() => toggleFilter(sev)}
                                disabled={count === 0}
                                className={cn(
                                  'h-7 px-2 rounded-lg text-[10px] font-semibold leading-none whitespace-nowrap border transition-all',
                                  active
                                    ? cn(cfg.text, 'bg-current/10 border-current')
                                    : 'bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:border-slate-300',
                                  count === 0 && 'opacity-40 cursor-not-allowed',
                                )}
                              >
                                {cfg.label} <span className="tabular-nums">{count}</span>
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {/* Bias Pattern row */}
                      <div className="space-y-1.5 min-w-0">
                        <span className="block text-[11px] text-slate-400">
                          {t('filterBiasPattern')}
                        </span>
                        <div className="flex flex-nowrap gap-1 overflow-x-auto pb-0.5">
                          <button
                            onClick={() => setActiveTypeFilters(new Set())}
                            className={cn(
                              'h-7 px-2 rounded-lg text-[10px] font-semibold leading-none whitespace-nowrap border transition-all',
                              activeTypeFilters.size === 0
                                ? 'bg-pride-purple text-white border-pride-purple'
                                : 'bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:border-pride-purple/40',
                            )}
                          >
                            {t('filterAllPatterns')}
                          </button>
                          {Object.entries(llmCategoryConfig).map(([cat, lvl]) => {
                            const active = activeTypeFilters.has(cat);
                            const count = confidenceFiltered.filter(r => r.category === cat).length;
                            return (
                              <button
                                key={cat}
                                onClick={() => toggleTypeFilter(cat)}
                                disabled={count === 0}
                                className={cn(
                                  'h-7 px-2 rounded-lg text-[10px] font-semibold leading-none whitespace-nowrap transition-all border',
                                  active
                                    ? cn(lvl.pill, 'border-current')
                                    : 'bg-white dark:bg-slate-800 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-700 hover:border-slate-300',
                                  count === 0 && 'opacity-40 cursor-not-allowed',
                                )}
                              >
                                {lvl.label}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center justify-between gap-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 px-3 py-2 text-xs text-slate-500 dark:text-slate-400">
                      <span>
                        {t('filterScopeShowing', {
                          shown: filteredResults.length,
                          total: confidenceFiltered.length,
                        })}
                      </span>
                      <button
                        onClick={() => { setActiveFilters(new Set()); setActiveTypeFilters(new Set()); }}
                        className="font-medium text-pride-purple hover:text-pride-pink transition-colors whitespace-nowrap flex-shrink-0"
                      >
                        {t('filterClear')}
                      </button>
                    </div>
                  </motion.div>

                  {/* Issues list — individual cards */}
                  <div
                    ref={issuesListRef}
                    className="flex flex-col gap-2 flex-shrink-0"
                    role="list"
                    aria-label={t('a11y.issuesList')}
                  >
                    {analysis.results.length === 0 ? (
                      <div className="p-8 text-center glass rounded-lg border shadow-sm">
                        <div className="text-4xl mb-3">🎉</div>
                        <p className="text-green-600 dark:text-green-400 font-semibold text-sm">
                          {t('noIssuesFound')}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">{t('noIssuesMessage')}</p>
                      </div>
                    ) : filteredResults.length === 0 ? (
                      <div className="p-6 text-center glass rounded-lg border shadow-sm">
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                          {t('filterNoMatch')}
                        </p>
                      </div>
                    ) : (
                      filteredResults.map((result, displayIdx) => {
                        const origIdx = analysis.results.indexOf(result);
                        const cfg = categoryConfig[result.severity];
                        return (
                          <motion.button
                            key={origIdx}
                            data-result-idx={origIdx}
                            onClick={() => handleIssueClick(result, origIdx)}
                            className={cn(
                              'w-full text-start rounded-lg border bg-white dark:bg-slate-900 shadow-sm',
                              'border-l-[3px] transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pride-purple',
                              selectedResultIndex === origIdx
                                ? 'ring-1 ring-pride-purple/30 shadow-md'
                                : 'hover:shadow-md'
                            )}
                            style={{ borderLeftColor: severityBorderColor[result.severity] }}
                            role="listitem"
                            tabIndex={0}
                            initial={{ opacity: 0, x: isHebrew ? -10 : 10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: displayIdx * 0.04 }}
                          >
                            <div className="px-3 py-2.5">
                              {/* Number + phrase + badges */}
                              <div className="flex items-start justify-between gap-2 mb-1.5">
                                <div className="flex items-center gap-2 min-w-0">
                                  <span className="text-[10px] font-bold text-slate-300 dark:text-slate-600 flex-shrink-0 w-4 text-right tabular-nums">
                                    {displayIdx + 1}
                                  </span>
                                  <p className="font-semibold text-sm text-slate-800 dark:text-white leading-snug truncate">
                                    &ldquo;{result.phrase}&rdquo;
                                  </p>
                                </div>
                                <div className="flex items-center gap-1.5 flex-shrink-0">
                                  <span className={cn(
                                    'flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full border border-current',
                                    cfg.text,
                                  )}>
                                    <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', cfg.dot)} />
                                    {cfg.label}
                                  </span>
                                  {result.category && llmCategoryConfig[result.category] && (
                                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400">
                                      {llmCategoryConfig[result.category].label}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {/* Explanation */}
                              {result.explanation && (
                                <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed pl-6">
                                  {result.explanation}
                                </p>
                              )}

                              {/* Suggested fix */}
                              {result.suggestion && (
                                <p className="text-[11px] mt-1 pl-6 leading-relaxed">
                                  <span className="text-pride-purple font-medium italic">{t('suggestedFix')} </span>
                                  <span className="text-slate-500 dark:text-slate-400 italic">{result.suggestion}</span>
                                </p>
                              )}
                            </div>
                          </motion.button>
                        );
                      })
                    )}
                  </div>


                  {/* Guest prompt */}
                  {!user && showGuestPrompt && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.3 }}
                      className="p-4 bg-gradient-to-r from-pride-purple/10 to-pride-blue/10 rounded-xl border border-pride-purple/20 flex-shrink-0"
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

      <AnnotationSidePanel
        annotation={selectedAnnotation}
        open={sidePanelOpen}
        onOpenChange={setSidePanelOpen}
        locale={locale}
        isPrivate={privateMode}
        runId={currentRunId}
      />
      <ContactModal
        open={contactOpen}
        onClose={() => setContactOpen(false)}
        analysis={viewState === 'results' ? analysis : null}
        fileName={fileName}
        locale={locale}
      />
      <ConfirmDialog
        open={pendingNav !== null}
        title={pendingNav?.source === 'results' ? t('switchLangWarning.title') : t('leaveWarning.title')}
        description={pendingNav?.source === 'results' ? t('switchLangWarning.message') : t('leaveWarning.message')}
        confirmLabel={pendingNav?.source === 'results' ? t('switchLangWarning.leave') : t('leaveWarning.leave')}
        cancelLabel={pendingNav?.source === 'results' ? t('switchLangWarning.stay') : t('leaveWarning.stay')}
        variant={pendingNav?.source === 'results' ? 'default' : 'danger'}
        onConfirm={confirmLeave}
        onCancel={() => setPendingNav(null)}
      />
    </>
  );
}
