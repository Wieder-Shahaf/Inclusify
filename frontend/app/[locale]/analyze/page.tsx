'use client';

import { useState, useCallback, useEffect } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import AnnotationSidePanel from '@/components/AnnotationSidePanel';
import SeverityBadge from '@/components/SeverityBadge';
import PaperUpload from '@/components/PaperUpload';
import ProcessingAnimation from '@/components/ProcessingAnimation';
import AnalysisSummary from '@/components/AnalysisSummary';
import IssueTooltip from '@/components/IssueTooltip';
import HealthWarningBanner from '@/components/HealthWarningBanner';
import { Annotation } from '@/components/AnnotatedText';
import { getSampleText, analyzeDemoText } from '@/lib/utils/demoData';
import { analyzeText, uploadFile, healthCheck } from '@/lib/api/client';
import { useAuth } from '@/contexts/AuthContext';
import { RotateCcw, FileText, ChevronLeft, ChevronRight, Scan, BarChart3, ShieldCheck } from 'lucide-react';

type ViewState = 'upload' | 'processing' | 'results';

interface AnalysisData {
  text: string;
  annotations: Annotation[];
  results: Array<{
    phrase: string;
    severity: 'outdated' | 'biased' | 'offensive' | 'incorrect';
    explanation: string;
    suggestion?: string;
    references?: Array<{ label: string; url: string }>;
  }>;
  counts: Record<'outdated' | 'biased' | 'offensive' | 'incorrect', number>;
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
  counts: { outdated: 0, biased: 0, offensive: 0, incorrect: 0 },
  summary: { totalIssues: 0, score: 100, recommendations: [] },
};

// Demo mode toggle: when true, uses local demo data instead of real API
const USE_DEMO = process.env.NEXT_PUBLIC_USE_DEMO_MODE === 'true';

export default function AnalyzePage() {
  const t = useTranslations('analyzer');
  const locale = useLocale();
  const isHebrew = locale === 'he';
  const { user } = useAuth();

  const [viewState, setViewState] = useState<ViewState>('upload');
  const [fileName, setFileName] = useState('');
  const [analysis, setAnalysis] = useState<AnalysisData>(emptyAnalysis);
  const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [analysisMode, setAnalysisMode] = useState<'llm' | 'hybrid' | 'rules_only' | null>(null);
  const [showGuestPrompt, setShowGuestPrompt] = useState(true);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [processingStage, setProcessingStage] = useState<'uploading' | 'parsing' | 'analyzing' | 'generating' | 'complete'>('uploading');
  const [showExtendedWait, setShowExtendedWait] = useState(false);

  // Health check on mount with 30-second polling
  useEffect(() => {
    const checkHealth = async () => {
      const healthy = await healthCheck();
      setBackendHealthy(healthy);
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Extended wait timer - shows message after 15 seconds of processing
  useEffect(() => {
    if (viewState !== 'processing' || USE_DEMO) {
      setShowExtendedWait(false);
      return;
    }
    const timer = setTimeout(() => {
      setShowExtendedWait(true);
    }, 15000);
    return () => clearTimeout(timer);
  }, [viewState]);

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
  }, [t]);

  const handleFileSelect = useCallback(async (file: File) => {
    setErrorMessage(null);  // Clear any previous error
    setFileName(file.name);
    setViewState('processing');

    if (USE_DEMO) {
      // Demo path: store file for demo processing animation to handle
      setPendingFile(file);
      return;
    }

    // Real API path
    try {
      setProcessingStage('uploading');

      // Upload and extract text
      const uploadResult = await uploadFile(file);

      setProcessingStage('analyzing');

      // Analyze the extracted text
      const result = await analyzeText(uploadResult.text, {
        language: locale as 'en' | 'he' | 'auto',
        privateMode: true,
      });

      setProcessingStage('complete');

      // Calculate score using severity weights (offensive > incorrect > biased > outdated)
      const weights = { outdated: 1, biased: 2, incorrect: 3, offensive: 4 };
      const wordCount = uploadResult.text.split(/\s+/).filter(Boolean).length;
      const totalWeightedIssues =
        result.counts.outdated * weights.outdated +
        result.counts.biased * weights.biased +
        result.counts.incorrect * weights.incorrect +
        result.counts.offensive * weights.offensive;
      const score = Math.max(0, Math.round(100 - (totalWeightedIssues / Math.max(wordCount, 1)) * 200));

      // Generate recommendations based on issue counts
      const recommendations: string[] = [];
      if (result.counts.offensive > 0) recommendations.push(t('recommendations.offensive'));
      if (result.counts.incorrect > 0) recommendations.push(t('recommendations.incorrect'));
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
    } catch (error) {
      console.error('Analysis failed:', error);
      handleApiError(error);
    }
  }, [locale, t, handleApiError]);

  const handleUseSample = useCallback(() => {
    setFileName(t('sampleFileName'));
    setViewState('processing');
  }, [t]);

  const handleProcessingComplete = useCallback(() => {
    const sampleText = getSampleText(locale);
    const recommendations = {
      outdated: t('recommendations.outdated'),
      biased: t('recommendations.biased'),
      offensive: t('recommendations.offensive'),
      incorrect: t('recommendations.incorrect'),
      excellent: t('recommendations.excellent'),
    };
    const result = analyzeDemoText(sampleText, locale, { recommendations });
    setAnalysis({
      text: sampleText,
      ...result,
    });
    setViewState('results');
  }, [locale, t]);

  const handleReset = useCallback(() => {
    setViewState('upload');
    setFileName('');
    setAnalysis(emptyAnalysis);
    setSelectedAnnotation(null);
    setSidePanelOpen(false);
    setAnalysisMode(null);
    setPendingFile(null);
    setErrorMessage(null);
    setShowExtendedWait(false);
    setProcessingStage('uploading');
    setShowGuestPrompt(true);
  }, []);

  const handleIssueClick = useCallback((result: AnalysisData['results'][0]) => {
    const annotation = analysis.annotations.find(
      (a) => a.label.toLowerCase() === result.phrase.toLowerCase()
    );
    if (annotation) {
      setSelectedAnnotation(annotation);
      setSidePanelOpen(true);
    }
  }, [analysis.annotations]);

  const handleAnnotationClick = useCallback((annotation: Annotation) => {
    setSelectedAnnotation(annotation);
    setSidePanelOpen(true);
  }, []);

  // Render highlighted text with tooltips
  const renderHighlightedText = () => {
    const { text, annotations } = analysis;
    if (!text) return null;
    if (annotations.length === 0) {
      return <span className="whitespace-pre-wrap">{text}</span>;
    }

    const parts: Array<{ content: string; annotation?: Annotation }> = [];
    let cursor = 0;

    // Sort and filter overlapping annotations
    const sorted = [...annotations].sort((a, b) => a.start - b.start);
    const nonOverlapping: Annotation[] = [];
    let lastEnd = -1;

    for (const ann of sorted) {
      if (ann.start >= lastEnd) {
        nonOverlapping.push(ann);
        lastEnd = ann.end;
      }
    }

    for (const ann of nonOverlapping) {
      if (ann.start > cursor) {
        parts.push({ content: text.slice(cursor, ann.start) });
      }
      parts.push({ content: text.slice(ann.start, ann.end), annotation: ann });
      cursor = ann.end;
    }
    if (cursor < text.length) {
      parts.push({ content: text.slice(cursor) });
    }

    return (
      <span className="whitespace-pre-wrap leading-relaxed">
        {parts.map((part, idx) =>
          part.annotation ? (
            <IssueTooltip
              key={idx}
              annotation={part.annotation}
              onOpenSidePanel={() => handleAnnotationClick(part.annotation!)}
            >
              {part.content}
            </IssueTooltip>
          ) : (
            <span key={idx}>{part.content}</span>
          )
        )}
      </span>
    );
  };

  const totalIssues = analysis.counts.outdated + analysis.counts.biased + analysis.counts.offensive + analysis.counts.incorrect;
  const wordCount = analysis.text.split(/\s+/).filter(Boolean).length;

  // Prepare translations for child components
  const uploadTranslations = {
    title: t('uploadTitle'),
    description: t('uploadDesc'),
    dragDrop: t('dragDrop'),
    trySample: t('trySample'),
    dropHere: t('dropHere'),
    chooseDifferent: t('chooseDifferent'),
    analyzePaper: t('analyzePaper'),
    fileError: t('fileError'),
    fileSizeError: t('fileSizeError'),
    or: t('or'),
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
    offensive: t('summaryCard.offensive'),
    incorrect: t('summaryCard.incorrect'),
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

              {/* Upload Component */}
              <PaperUpload
                onFileSelect={handleFileSelect}
                onUseSample={handleUseSample}
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
                stage={USE_DEMO ? undefined : processingStage}
                onComplete={USE_DEMO ? handleProcessingComplete : undefined}
                translations={processingTranslations}
                showExtendedWait={showExtendedWait}
                extendedWaitMessage={t('processing.takingLonger')}
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
              className="h-[calc(100vh-140px)] flex flex-col px-4 py-4"
            >
              {/* Results Header - Fixed */}
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
                    <h2 className="font-semibold text-lg text-slate-800 dark:text-white flex items-center gap-2">
                      <FileText className="w-5 h-5 text-pride-purple" />
                      {fileName}
                      {analysisMode === 'rules_only' && (
                        <span
                          className="ml-2 px-2 py-0.5 text-xs rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
                          title={t('basicAnalysisModeDesc')}
                        >
                          {t('basicAnalysisMode')}
                        </span>
                      )}
                    </h2>
                    <p className="text-sm text-slate-500">
                      {totalIssues} {totalIssues === 1 ? t('issueFound') : t('issuesFoundPlural')}
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleReset}
                  className="btn-ghost px-4 py-2 rounded-lg text-sm flex items-center gap-2"
                >
                  <RotateCcw className="w-4 h-4" />
                  {t('analyzeAnother')}
                </button>
              </div>

              {/* Main Content Grid - Flexible */}
              <div className={`flex-1 min-h-0 grid gap-4 ${isHebrew ? 'lg:grid-cols-[380px,1fr]' : 'lg:grid-cols-[1fr,380px]'}`}>
                {/* Text Panel with Highlights */}
                <div className={`glass rounded-xl border overflow-hidden flex flex-col min-h-0 max-h-full ${isHebrew ? 'lg:order-2' : ''}`}>
                  <div className="px-4 py-3 border-b bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between flex-shrink-0">
                    <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
                      {t('documentContent')}
                    </span>
                    <span className="text-xs text-slate-400">
                      {t('hoverHint')}
                    </span>
                  </div>
                  <div
                    className="flex-1 p-6 overflow-y-auto text-sm text-slate-700 dark:text-slate-200 scroll-smooth min-h-0"
                    style={{ scrollBehavior: 'smooth' }}
                    dir={isHebrew ? 'rtl' : 'ltr'}
                  >
                    {renderHighlightedText()}
                  </div>
                </div>

                {/* Right Panel: Summary + Issues - Scrollable */}
                <div className={`flex flex-col gap-4 min-h-0 max-h-full overflow-y-auto scroll-smooth pb-4 ${isHebrew ? 'lg:order-1' : ''}`} style={{ scrollBehavior: 'smooth' }}>
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
                    <div className="px-4 py-3 border-b bg-slate-50/50 dark:bg-slate-800/50 flex-shrink-0">
                      <h3 className="text-sm font-semibold flex items-center gap-2">
                        {t('issuesFound')}
                        <span className="px-2 py-0.5 text-xs rounded-full bg-pride-purple/20 text-pride-purple">
                          {analysis.results.length}
                        </span>
                      </h3>
                    </div>
                    <div className="divide-y divide-slate-100 dark:divide-slate-800">
                      {analysis.results.length === 0 ? (
                        <div className="p-6 text-center">
                          <div className="text-3xl mb-2">🎉</div>
                          <p className="text-green-600 dark:text-green-400 font-medium">{t('noIssuesFound')}</p>
                          <p className="text-sm text-slate-500 mt-1">{t('noIssuesMessage')}</p>
                        </div>
                      ) : (
                        analysis.results.map((result, i) => (
                          <motion.button
                            key={i}
                            onClick={() => handleIssueClick(result)}
                            className="w-full px-4 py-3 text-start hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                            initial={{ opacity: 0, x: isHebrew ? -20 : 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.05 }}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-sm text-slate-800 dark:text-white truncate">
                                  &ldquo;{result.phrase}&rdquo;
                                </p>
                                {result.suggestion && (
                                  <p className="text-xs text-pride-purple mt-1 truncate">{isHebrew ? '←' : '→'} {result.suggestion}</p>
                                )}
                              </div>
                              <SeverityBadge level={result.severity} />
                            </div>
                          </motion.button>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Guest Prompt - show after analysis for non-authenticated users */}
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

      {/* Side Panel for Issue Details */}
      <AnnotationSidePanel
        annotation={selectedAnnotation}
        open={sidePanelOpen}
        onOpenChange={setSidePanelOpen}
      />
    </>
  );
}
