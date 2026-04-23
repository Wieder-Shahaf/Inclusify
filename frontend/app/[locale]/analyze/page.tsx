'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import AnnotationSidePanel from '@/components/AnnotationSidePanel';
import SeverityBadge from '@/components/SeverityBadge';
import PaperUpload from '@/components/PaperUpload';
import ProcessingAnimation from '@/components/ProcessingAnimation';
import HealthWarningBanner from '@/components/HealthWarningBanner';
import { Annotation } from '@/components/AnnotatedText';
import DocumentViewer from '@/components/DocumentViewer';
import { analyzeText, uploadFile, healthCheck, modelHealthCheck, BboxAnnotation, PageSize } from '@/lib/api/client';
import { exportReport } from '@/lib/exportReport';
import { useAuth } from '@/contexts/AuthContext';
import { useLiveAnnouncer } from '@/contexts/LiveAnnouncerContext';
import { useKeyboardNavigation } from '@/hooks/useKeyboardNavigation';
import {
  RotateCcw, FileText, ChevronLeft, ChevronRight, Scan, BarChart3, ShieldCheck,
  Lock, Mail, Download, AlertCircle, CheckCircle2, TrendingUp, Lightbulb, ArrowRight,
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

function getScoreRingColor(score: number): string {
  if (score >= 90) return '#22c55e';
  if (score >= 70) return '#f59e0b';
  if (score >= 50) return '#f97316';
  return '#ef4444';
}

function getScoreBg(score: number): string {
  if (score >= 90) return 'bg-green-500';
  if (score >= 70) return 'bg-amber-500';
  if (score >= 50) return 'bg-orange-500';
  return 'bg-red-500';
}

export default function AnalyzePage() {
  const t = useTranslations('analyzer');
  const locale = useLocale();
  const isHebrew = locale === 'he';
  const { user } = useAuth();
  const { announce } = useLiveAnnouncer();
  const issuesListRef = useRef<HTMLDivElement>(null);
  const textPanelRef = useRef<HTMLDivElement>(null);

  const [viewState, setViewState] = useState<ViewState>('upload');
  const [fileName, setFileName] = useState('');
  const [analysis, setAnalysis] = useState<AnalysisData>(emptyAnalysis);
  const [activeFilters, setActiveFilters] = useState<Set<Severity>>(new Set());
  const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);
  const [selectedResultIndex, setSelectedResultIndex] = useState<number | null>(null);
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [modelAvailable, setModelAvailable] = useState<boolean | null>(null);
  const [analysisMode, setAnalysisMode] = useState<'llm' | 'hybrid' | 'rules_only' | null>(null);
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
    setErrorMessage(null);
    setFileName(file.name);
    setViewState('processing');
    announce(t('a11y.uploadStarted'));

    try {
      setProcessingStage('uploading');
      const uploadResult = await uploadFile(file);
      setProcessingStage('analyzing');

      const result = await analyzeText(uploadResult.text, {
        language: locale as 'en' | 'he' | 'auto',
        privateMode,
        useAuth: true,
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

      const weights = { outdated: 1, biased: 2, factually_incorrect: 3, potentially_offensive: 4 };
      const wc = uploadResult.text.split(/\s+/).filter(Boolean).length;
      const totalWeightedIssues =
        result.counts.outdated * weights.outdated +
        result.counts.biased * weights.biased +
        result.counts.factually_incorrect * weights.factually_incorrect +
        result.counts.potentially_offensive * weights.potentially_offensive;
      const score = Math.max(0, Math.round(100 - (totalWeightedIssues / Math.max(wc, 1)) * 200));

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
      setCurrentRunId(result.runId);
      // Store document viewer metadata
      setUploadedFile(file);
      setDocInputType(uploadResult.inputType);
      setBboxAnnotations(uploadResult.bboxAnnotations ?? null);
      setPageSizes(uploadResult.pageSizes ?? null);
      setMarkdownText(uploadResult.markdownText ?? null);
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

  const handleIssueClick = useCallback((result: AnalysisData['results'][0], index: number) => {
    const annotation = analysis.annotations.find(
      (a) => a.label.toLowerCase() === result.phrase.toLowerCase()
    );
    setSelectedResultIndex(index);
    if (annotation) {
      setSelectedAnnotation(annotation);
      setSidePanelOpen(true);
      const el = document.getElementById(`ann-${annotation.start}`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [analysis.annotations]);

  const handleAnnotationClick = useCallback((annotation: Annotation) => {
    setSelectedAnnotation(annotation);
    setSidePanelOpen(true);
    const idx = analysis.results.findIndex(
      (r) => r.phrase.toLowerCase() === annotation.label.toLowerCase()
    );
    if (idx !== -1) setSelectedResultIndex(idx);
  }, [analysis.results]);

  const handleExport = useCallback(() => {
    exportReport(analysis, { fileName, locale });
  }, [analysis, fileName, locale]);

  const toggleFilter = useCallback((sev: Severity) => {
    setActiveFilters(prev => {
      const next = new Set(prev);
      if (next.has(sev)) next.delete(sev); else next.add(sev);
      return next;
    });
  }, []);

  const filteredResults = activeFilters.size === 0
    ? analysis.results
    : analysis.results.filter(r => activeFilters.has(r.severity));

  useKeyboardNavigation({
    containerRef: issuesListRef,
    itemSelector: 'button[role="listitem"]',
    enabled: viewState === 'results' && analysis.results.length > 0,
    onSelect: (_, index) => {
      if (analysis.results[index]) handleIssueClick(analysis.results[index], index);
    },
  });

  const totalIssues =
    analysis.counts.outdated +
    analysis.counts.biased +
    analysis.counts.potentially_offensive +
    analysis.counts.factually_incorrect;
  const wordCount = analysis.text.split(/\s+/).filter(Boolean).length;
  const score = analysis.summary.score;
  const circumference = 2 * Math.PI * 36;

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
      bar: 'bg-rose-500',
      dot: 'bg-rose-400',
      text: 'text-rose-600 dark:text-rose-400',
    },
    factually_incorrect: {
      label: t('summaryCard.factually_incorrect'),
      bar: 'bg-red-500',
      dot: 'bg-red-400',
      text: 'text-red-600 dark:text-red-400',
    },
  } as const;

  const maxCount = Math.max(...Object.values(analysis.counts), 1);
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
      {viewState === 'results' && analysisMode === 'rules_only' && (
        <HealthWarningBanner
          message={t('llmDownResults')}
          variant="error"
          linkHref={`/${locale}/glossary`}
          linkText={t('llmDownResultsLink')}
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

              <PaperUpload onFileSelect={handleFileSelect} translations={uploadTranslations} />

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
              className="h-[calc(100vh-140px)] flex flex-col px-4 py-4"
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
                      {analysisMode === 'rules_only' && (
                        <span
                          className="px-2 py-0.5 text-xs rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                          title={t('basicAnalysisModeDesc')}
                        >
                          {t('basicAnalysisMode')}
                        </span>
                      )}
                    </h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {totalIssues} {totalIssues === 1 ? t('issueFound') : t('issuesFoundPlural')}
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleReset}
                  className="btn-ghost px-3 py-2 rounded-lg text-sm flex items-center gap-2"
                >
                  <RotateCcw className="w-4 h-4" />
                  {t('analyzeAnother')}
                </button>
              </div>

              {/* Two-column grid — inline style avoids Tailwind JIT scan issues with dynamic arbitrary values */}
              <div
                className="flex-1 min-h-0 grid gap-4"
                style={{ gridTemplateColumns: 'minmax(0, 1fr) 440px' }}
              >
                {/* ── LEFT: Document Viewer ───────────────────────── */}
                <div className="glass rounded-xl border overflow-hidden flex flex-col min-h-0 max-h-full">
                  {/* Panel header */}
                  <div className="px-4 py-3 border-b bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between flex-shrink-0">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-pride-purple" />
                      <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                        {t('documentContent')}
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
                      inputType={docInputType}
                      text={analysis.text}
                      annotations={analysis.annotations}
                      uploadedFile={uploadedFile}
                      bboxAnnotations={bboxAnnotations}
                      pageSizes={pageSizes}
                      markdownText={markdownText}
                      onAnnotationClick={handleAnnotationClick}
                      isHebrew={isHebrew}
                    />
                  </div>

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

                {/* ── RIGHT: Analysis Panel ───────────────────────── */}
                <div
                  className="flex flex-col gap-3 min-h-0 max-h-full overflow-y-auto pb-4"
                  style={{ scrollBehavior: 'smooth' }}
                >
                  {/* Score Card */}
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4 }}
                    className="glass rounded-xl border p-5 flex-shrink-0 overflow-hidden relative"
                  >
                    {/* decorative glow */}
                    <div className="absolute top-0 right-0 w-44 h-44 opacity-[0.07] pointer-events-none">
                      <div className={cn('absolute inset-0 rounded-full blur-3xl', getScoreBg(score))} />
                    </div>

                    <div className="relative">
                      <p className="text-[11px] uppercase tracking-widest text-slate-400 mb-3 font-medium">
                        {t('summaryCard.score')}
                      </p>

                      <div className="flex items-center justify-between gap-4">
                        {/* Number + label */}
                        <div>
                          <div className="flex items-baseline gap-1.5">
                            <motion.span
                              className={cn('text-6xl font-black tabular-nums leading-none', getScoreColor(score))}
                              initial={{ scale: 0.6, opacity: 0 }}
                              animate={{ scale: 1, opacity: 1 }}
                              transition={{ type: 'spring', stiffness: 180, damping: 14, delay: 0.1 }}
                            >
                              {score}
                            </motion.span>
                            <span className="text-slate-400 text-xl">/100</span>
                          </div>
                          <div className="flex items-center gap-1.5 mt-2">
                            {score >= 70 ? (
                              <CheckCircle2 className={cn('w-4 h-4', getScoreColor(score))} />
                            ) : (
                              <AlertCircle className={cn('w-4 h-4', getScoreColor(score))} />
                            )}
                            <span className={cn('text-sm font-semibold', getScoreColor(score))}>
                              {scoreLabel}
                            </span>
                          </div>
                        </div>

                        {/* Ring progress */}
                        <div className="relative w-24 h-24 flex-shrink-0">
                          <svg className="w-full h-full -rotate-90" viewBox="0 0 96 96">
                            <circle
                              cx="48" cy="48" r="36"
                              strokeWidth="8" fill="none"
                              className="stroke-slate-100 dark:stroke-slate-800"
                            />
                            <motion.circle
                              cx="48" cy="48" r="36"
                              strokeWidth="8" fill="none"
                              stroke={getScoreRingColor(score)}
                              strokeLinecap="round"
                              initial={{ strokeDasharray: `0 ${circumference}` }}
                              animate={{ strokeDasharray: `${(score / 100) * circumference} ${circumference}` }}
                              transition={{ duration: 1.2, ease: 'easeOut', delay: 0.2 }}
                            />
                          </svg>
                          <div className="absolute inset-0 flex items-center justify-center">
                            <span className={cn('text-base font-bold', getScoreColor(score))}>{score}%</span>
                          </div>
                        </div>
                      </div>

                      {/* Stats row */}
                      <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-[11px] text-slate-400 mb-0.5 uppercase tracking-wide">
                            {t('summaryCard.totalIssues')}
                          </p>
                          <p className="text-2xl font-bold text-slate-800 dark:text-white">{totalIssues}</p>
                        </div>
                        <div>
                          <p className="text-[11px] text-slate-400 mb-0.5 uppercase tracking-wide">
                            {t('summaryCard.wordCount')}
                          </p>
                          <p className="text-2xl font-bold text-slate-800 dark:text-white">
                            {wordCount.toLocaleString()}
                          </p>
                        </div>
                      </div>
                    </div>
                  </motion.div>

                  {/* Category breakdown */}
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.08 }}
                    className="glass rounded-xl border p-4 flex-shrink-0"
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <BarChart3 className="w-4 h-4 text-pride-purple" />
                      <h3 className="text-sm font-semibold">{t('summaryCard.categories')}</h3>
                    </div>
                    <div className="space-y-2.5">
                      {(Object.keys(categoryConfig) as Severity[]).map((sev) => {
                        const cfg = categoryConfig[sev];
                        const count = analysis.counts[sev];
                        const pct = (count / maxCount) * 100;
                        return (
                          <div key={sev}>
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className={cn('font-medium', cfg.text)}>{cfg.label}</span>
                              <span className="font-bold text-slate-600 dark:text-slate-300 tabular-nums">
                                {count}
                              </span>
                            </div>
                            <div className="h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                              <motion.div
                                className={cn('h-full rounded-full', cfg.bar)}
                                initial={{ width: 0 }}
                                animate={{ width: `${pct}%` }}
                                transition={{ duration: 0.6, delay: 0.15 }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </motion.div>

                  {/* Issues list */}
                  <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.14 }}
                    className="glass rounded-xl border overflow-hidden flex-shrink-0"
                  >
                    <div className="px-4 py-3 border-b bg-slate-50/50 dark:bg-slate-800/50">
                      <div className="flex items-center justify-between mb-2.5">
                        <h3 className="text-sm font-semibold flex items-center gap-2">
                          {t('issuesFound')}
                          <span className="px-2 py-0.5 text-xs rounded-full bg-pride-purple/15 text-pride-purple font-bold">
                            {filteredResults.length}
                            {activeFilters.size > 0 && analysis.results.length !== filteredResults.length && (
                              <span className="font-normal text-pride-purple/60"> / {analysis.results.length}</span>
                            )}
                          </span>
                        </h3>
                        {activeFilters.size > 0 && (
                          <button
                            onClick={() => setActiveFilters(new Set())}
                            className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                          >
                            {t('filterClear') || 'Clear'}
                          </button>
                        )}
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {(Object.keys(categoryConfig) as Severity[]).map((sev) => {
                          const cfg = categoryConfig[sev];
                          const active = activeFilters.has(sev);
                          const count = analysis.counts[sev];
                          return (
                            <button
                              key={sev}
                              onClick={() => toggleFilter(sev)}
                              disabled={count === 0}
                              className={cn(
                                'flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border transition-all',
                                active
                                  ? 'border-current bg-current/10'
                                  : 'border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600',
                                active && cfg.text,
                                count === 0 && 'opacity-40 cursor-not-allowed',
                              )}
                            >
                              <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', cfg.dot)} />
                              {cfg.label}
                              <span className="opacity-60 tabular-nums">{count}</span>
                            </button>
                          );
                        })}
                      </div>
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
                          <p className="text-green-600 dark:text-green-400 font-semibold text-sm">
                            {t('noIssuesFound')}
                          </p>
                          <p className="text-xs text-slate-500 mt-1">{t('noIssuesMessage')}</p>
                        </div>
                      ) : filteredResults.length === 0 ? (
                        <div className="p-6 text-center">
                          <p className="text-sm text-slate-500 dark:text-slate-400">
                            {t('filterNoMatch') || 'No issues match the selected filters.'}
                          </p>
                        </div>
                      ) : (
                        filteredResults.map((result) => {
                          const origIdx = analysis.results.indexOf(result);
                          return (
                          <motion.button
                            key={origIdx}
                            onClick={() => handleIssueClick(result, origIdx)}
                            className={cn(
                              'w-full px-4 py-3.5 text-start transition-all border-l-[3px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pride-purple focus-visible:ring-inset',
                              selectedResultIndex === origIdx
                                ? 'bg-pride-purple/5 dark:bg-pride-purple/10 border-l-pride-purple'
                                : 'border-l-transparent hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:border-l-slate-200 dark:hover:border-l-slate-700'
                            )}
                            role="listitem"
                            tabIndex={0}
                            initial={{ opacity: 0, x: isHebrew ? -10 : 10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: origIdx * 0.04 }}
                          >
                            {/* Phrase + badge */}
                            <div className="flex items-start justify-between gap-2 mb-1.5">
                              <p className="font-semibold text-sm text-slate-800 dark:text-white leading-snug">
                                &ldquo;{result.phrase}&rdquo;
                              </p>
                              <div className="flex-shrink-0 mt-0.5">
                                <SeverityBadge level={result.severity} />
                              </div>
                            </div>

                            {/* Explanation */}
                            {result.explanation && (
                              <p className="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 mb-2 leading-relaxed">
                                {result.explanation}
                              </p>
                            )}

                            {/* Suggestion */}
                            {result.suggestion && (
                              <div className="flex items-center gap-1.5 text-xs text-pride-purple font-medium">
                                <ArrowRight className="w-3 h-3 flex-shrink-0" />
                                <span className="truncate">{result.suggestion}</span>
                              </div>
                            )}
                          </motion.button>
                        );})
                      )}
                    </div>
                  </motion.div>

                  {/* Recommendations */}
                  {analysis.summary.recommendations.length > 0 && totalIssues > 0 && (
                    <motion.div
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4, delay: 0.2 }}
                      className="glass rounded-xl border p-4 flex-shrink-0"
                    >
                      <div className="flex items-center gap-2 mb-3">
                        <Lightbulb className="w-4 h-4 text-pride-purple" />
                        <h3 className="text-sm font-semibold">{t('summaryCard.recommendations')}</h3>
                      </div>
                      <ul className="space-y-2">
                        {analysis.summary.recommendations.map((rec, idx) => (
                          <motion.li
                            key={idx}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.2 + idx * 0.07 }}
                            className="flex items-start gap-2 text-xs text-slate-600 dark:text-slate-300"
                          >
                            <TrendingUp className="w-3.5 h-3.5 text-pride-purple flex-shrink-0 mt-0.5" />
                            <span>{rec}</span>
                          </motion.li>
                        ))}
                      </ul>
                    </motion.div>
                  )}

                  {/* Action buttons */}
                  <div className="flex gap-2 flex-shrink-0">
                    <motion.button
                      onClick={handleExport}
                      className="flex-1 py-2.5 px-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-pride-purple/40 hover:bg-pride-purple/5 transition-all flex items-center justify-center gap-2 text-slate-600 dark:text-slate-400 text-sm"
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                    >
                      <Download className="w-4 h-4" />
                      <span className="font-medium">{t('exportReport')}</span>
                    </motion.button>
                    <motion.button
                      onClick={() => setContactOpen(true)}
                      className="flex-1 py-2.5 px-3 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-pride-purple/40 hover:bg-pride-purple/5 transition-all flex items-center justify-center gap-2 text-slate-600 dark:text-slate-400 text-sm"
                      whileHover={{ scale: 1.01 }}
                      whileTap={{ scale: 0.99 }}
                    >
                      <Mail className="w-4 h-4" />
                      <span className="font-medium">{t('contactUs')}</span>
                    </motion.button>
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
    </>
  );
}
