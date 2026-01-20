'use client';

import { useState, useRef } from 'react';
import { useTranslations } from 'next-intl';
import AnnotationSidePanel from '@/components/AnnotationSidePanel';
import SeverityBadge from '@/components/SeverityBadge';
import { analyzeText, uploadFile, type AnalysisResult } from '@/lib/api/client';
import { mockAnalyze } from '@/lib/utils/mock';
import { Annotation } from '@/components/AnnotatedText';
import { cn } from '@/lib/utils';

const emptyAnalysis: AnalysisResult = {
  annotations: [],
  results: [],
  counts: { outdated: 0, biased: 0, offensive: 0, incorrect: 0 },
  originalText: '',
};

export default function AnalyzePage() {
  const t = useTranslations();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState('');
  const [ran, setRan] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult>(emptyAnalysis);
  const [privateMode, setPrivateMode] = useState(true);
  const [sensitivity, setSensitivity] = useState(3);
  const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const counts = analysis.counts;
  const totalIssues = counts.outdated + counts.biased + counts.offensive + counts.incorrect;

  const run = async () => {
    if (!text.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const result = await analyzeText(text, { privateMode });
      setAnalysis(result);
      setRan(true);
    } catch (err) {
      console.error('Analysis failed:', err);
      setError(err instanceof Error ? err.message : 'Analysis failed. Is the backend running?');
      const mockResult = mockAnalyze(text);
      setAnalysis({ ...mockResult, originalText: text });
      setRan(true);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setLoading(true);
    setError(null);

    try {
      const result = await uploadFile(files[0]);
      setText(result.text);
    } catch (err) {
      console.error('Upload failed:', err);
      setError(err instanceof Error ? err.message : 'Upload failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const handleIssueClick = (result: typeof analysis.results[0]) => {
    const annotation = analysis.annotations.find(
      (a) => a.label.toLowerCase() === result.phrase.toLowerCase()
    );
    if (annotation) {
      setSelectedAnnotation(annotation);
      setSidePanelOpen(true);
    }
  };

  // Render text with inline highlights (no overlap issues)
  const renderHighlightedText = () => {
    if (!text) return null;
    if (analysis.annotations.length === 0) {
      return <span className="whitespace-pre-wrap">{text}</span>;
    }

    const parts: Array<{ content: string; annotation?: Annotation }> = [];
    let cursor = 0;

    // Sort and filter overlapping annotations (keep first occurrence only)
    const sorted = [...analysis.annotations].sort((a, b) => a.start - b.start);
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

    const severityColors: Record<string, string> = {
      outdated: 'bg-sky-200 dark:bg-sky-900/50 border-b-2 border-sky-500',
      biased: 'bg-amber-200 dark:bg-amber-900/50 border-b-2 border-amber-500',
      offensive: 'bg-rose-200 dark:bg-rose-900/50 border-b-2 border-rose-500',
      incorrect: 'bg-red-200 dark:bg-red-900/50 border-b-2 border-red-500',
    };

    return (
      <span className="whitespace-pre-wrap">
        {parts.map((part, idx) =>
          part.annotation ? (
            <mark
              key={idx}
              onClick={(e) => {
                e.stopPropagation();
                setSelectedAnnotation(part.annotation!);
                setSidePanelOpen(true);
              }}
              className={cn(
                'cursor-pointer rounded-sm px-0.5 transition-all hover:opacity-70',
                severityColors[part.annotation.severity] || severityColors.biased
              )}
              title={part.annotation.suggestion ? `→ ${part.annotation.suggestion}` : undefined}
            >
              {part.content}
            </mark>
          ) : (
            <span key={idx}>{part.content}</span>
          )
        )}
      </span>
    );
  };

  return (
    <>
      <div className="py-4">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3 p-2 glass rounded-lg border">
          <div className="flex items-center gap-3">
            {/* Upload Button */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="btn-ghost px-3 py-1.5 rounded-lg text-sm flex items-center gap-2"
              disabled={loading}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              Upload
            </button>

            {/* Private Mode */}
            <label className="inline-flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                className="h-4 w-4 rounded"
                checked={privateMode}
                onChange={(e) => setPrivateMode(e.target.checked)}
              />
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                {t('app.privateMode')}
              </span>
            </label>

            {/* Settings */}
            <div className="relative">
              <button
                onClick={() => setSettingsOpen(!settingsOpen)}
                className="btn-ghost px-3 py-1.5 rounded-lg text-sm flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {t('analyzer.settings')}
              </button>
              {settingsOpen && (
                <div className="absolute left-0 mt-2 w-72 glass border rounded-xl p-4 z-20 shadow-lg">
                  <div className="flex items-center justify-between">
                    <label className="text-sm">Sensitivity</label>
                    <span className="text-sm font-medium">{sensitivity}</span>
                  </div>
                  <input
                    type="range"
                    min={1}
                    max={5}
                    value={sensitivity}
                    onChange={(e) => setSensitivity(Number(e.target.value))}
                    className="w-full mt-2"
                  />
                  <fieldset className="mt-4 text-sm space-y-2">
                    <legend className="font-medium mb-2">Categories</legend>
                    {['outdated', 'biased', 'offensive', 'incorrect'].map((c) => (
                      <label key={c} className="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" defaultChecked className="h-4 w-4 rounded" />
                        <SeverityBadge level={c as any} />
                      </label>
                    ))}
                  </fieldset>
                </div>
              )}
            </div>
          </div>

          {/* Analyze Button */}
          <button
            onClick={run}
            disabled={loading || !text.trim()}
            className="btn-primary px-5 py-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Analyzing...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
                {t('analyzer.analyzeBtn')}
              </>
            )}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}

        {/* Main Content: Editor + Issues Panel */}
        <div className="grid gap-4 lg:grid-cols-[1fr,300px]" style={{ height: 'calc(100vh - 200px)', minHeight: '400px', maxHeight: '600px' }}>
          {/* Text Editor with Highlights */}
          <div className="glass rounded-xl border overflow-hidden flex flex-col">
            <div className="flex-1 p-4 overflow-auto">
              {/* Show textarea when not analyzed, highlighted text when analyzed */}
              {!ran ? (
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder={t('analyzer.placeholder') as string}
                  className="w-full h-full min-h-full resize-none bg-transparent outline-none leading-7"
                  aria-label="Text to analyze"
                />
              ) : (
                <div
                  className="leading-7 cursor-text"
                  onClick={() => setRan(false)} // Click to edit
                  title="Click to edit"
                >
                  {renderHighlightedText()}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between text-sm text-slate-500">
              <span>{text.length} chars</span>
              <div className="flex items-center gap-3">
                {ran && (
                  <button
                    onClick={() => setRan(false)}
                    className="text-pride-purple hover:underline text-xs"
                  >
                    Edit text
                  </button>
                )}
                {ran && (
                  <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Analyzed
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Issues Panel */}
          <div className="glass rounded-xl border overflow-hidden flex flex-col">
            <div className="p-3 border-b bg-slate-50/50 dark:bg-slate-800/50">
              <h2 className="font-semibold text-sm flex items-center gap-2">
                Issues
                {totalIssues > 0 && (
                  <span className="px-2 py-0.5 text-xs rounded-full bg-pride-purple/20 text-pride-purple">
                    {totalIssues}
                  </span>
                )}
              </h2>
            </div>

            {/* Summary Counts - Compact */}
            <div className="px-3 py-2 border-b flex flex-wrap gap-x-4 gap-y-1 text-xs">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-sky-500" />
                {counts.outdated}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                {counts.biased}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                {counts.offensive}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500" />
                {counts.incorrect}
              </span>
            </div>

            {/* Issues List */}
            <div className="flex-1 overflow-y-auto">
              {!ran && (
                <div className="p-4 text-center text-slate-500 text-xs">
                  Click "Analyze" to check your text
                </div>
              )}

              {ran && analysis.results.length === 0 && (
                <div className="p-4 text-center">
                  <div className="text-xl mb-1">🎉</div>
                  <div className="text-green-600 dark:text-green-400 text-sm font-medium">
                    No issues found!
                  </div>
                </div>
              )}

              {analysis.results.map((result, i) => (
                <div
                  key={i}
                  onClick={() => handleIssueClick(result)}
                  className="px-3 py-2 border-b last:border-b-0 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-sm truncate">
                      {result.phrase}
                    </span>
                    <SeverityBadge level={result.severity} />
                  </div>
                  {result.suggestion && (
                    <div className="mt-1 text-xs text-slate-500 truncate">
                      → {result.suggestion}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <AnnotationSidePanel
        annotation={selectedAnnotation}
        open={sidePanelOpen}
        onOpenChange={setSidePanelOpen}
      />
    </>
  );
}
