'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import {
  getHistory,
  getAnalysisDetail,
  deleteAnalysis,
  type HistoryEntry,
  type HistoryKPIs,
  type AnalysisDetail,
  type FindingDetail,
} from '@/lib/api/client';
import {
  FileText, Clock, AlertTriangle, TrendingUp, History, Loader2,
  BookOpen, Globe, Trash2, X, ChevronDown, ChevronUp, CheckCircle2,
} from 'lucide-react';

// ── helpers ────────────────────────────────────────────────────────────────

function computeScore(findings: number): number {
  return Math.max(0, Math.min(100, 100 - findings * 8));
}

function scoreLabel(score: number, locale: string): string {
  if (score >= 90) return locale === 'he' ? 'מצוין' : 'Excellent';
  if (score >= 70) return locale === 'he' ? 'טוב' : 'Good';
  if (score >= 50) return locale === 'he' ? 'דורש שיפור' : 'Needs Improvement';
  return locale === 'he' ? 'דורש תשומת לב' : 'Requires Attention';
}

function scoreColor(score: number): string {
  if (score >= 90) return '#22c55e';
  if (score >= 70) return '#84cc16';
  if (score >= 50) return '#f59e0b';
  return '#ef4444';
}

function scoreRingColor(score: number): string {
  if (score >= 90) return 'text-green-500';
  if (score >= 70) return 'text-lime-500';
  if (score >= 50) return 'text-amber-500';
  return 'text-red-500';
}

function scoreBg(score: number): string {
  if (score >= 90) return 'bg-green-50 dark:bg-green-950/30';
  if (score >= 70) return 'bg-lime-50 dark:bg-lime-950/30';
  if (score >= 50) return 'bg-amber-50 dark:bg-amber-950/30';
  return 'bg-red-50 dark:bg-red-950/30';
}

function severityColor(sev: string) {
  if (sev === 'high') return { dot: 'bg-red-400', text: 'text-red-600 dark:text-red-400', badge: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300' };
  if (sev === 'medium') return { dot: 'bg-amber-400', text: 'text-amber-600 dark:text-amber-400', badge: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300' };
  return { dot: 'bg-blue-400', text: 'text-blue-600 dark:text-blue-400', badge: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' };
}

function formatDate(iso: string | null, locale: string): string {
  if (!iso) return locale === 'he' ? 'לא ידוע' : 'Unknown';
  return new Date(iso).toLocaleDateString(locale === 'he' ? 'he-IL' : 'en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
  });
}

function docLabel(entry: HistoryEntry | AnalysisDetail, locale: string): string {
  return entry.title || entry.filename || (locale === 'he' ? 'טקסט ללא שם' : 'Untitled text');
}

// ── Score ring ─────────────────────────────────────────────────────────────

function ScoreRing({ score, size = 64 }: { score: number; size?: number }) {
  const r = size * 0.39;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = scoreColor(score);
  const cx = size / 2;
  return (
    <div className="relative flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90" viewBox={`0 0 ${size} ${size}`}>
        <circle cx={cx} cy={cx} r={r} fill="none" stroke="currentColor" strokeWidth="5"
          className="text-slate-200 dark:text-slate-700" />
        <circle cx={cx} cy={cx} r={r} fill="none" stroke={color} strokeWidth="5"
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round" />
      </svg>
      <span className="absolute text-sm font-bold" style={{ color, fontSize: size < 50 ? 10 : 14 }}>{score}</span>
    </div>
  );
}

// ── KPI card ───────────────────────────────────────────────────────────────

function KpiCard({ icon, label, value, sub, accent }: {
  icon: React.ReactNode; label: string; value: string | number; sub?: string; accent?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 flex items-start gap-4">
      <div className={`p-2.5 rounded-lg ${accent ?? 'bg-slate-100 dark:bg-slate-800'}`}>{icon}</div>
      <div>
        <p className="text-xs text-slate-500 dark:text-slate-400 font-medium uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-slate-900 dark:text-slate-100 mt-0.5">{value}</p>
        {sub && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ── Finding row ────────────────────────────────────────────────────────────

function FindingRow({ finding, locale }: { finding: FindingDetail; locale: string }) {
  const [open, setOpen] = useState(false);
  const isHe = locale === 'he';
  const col = severityColor(finding.severity);
  const sevLabel = finding.severity === 'high'
    ? (isHe ? 'גבוה' : 'High')
    : finding.severity === 'medium'
    ? (isHe ? 'בינוני' : 'Medium')
    : (isHe ? 'נמוך' : 'Low');

  return (
    <div className="border border-slate-100 dark:border-slate-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-start gap-3 p-3 text-left hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
      >
        <span className={`mt-1 inline-block w-2 h-2 rounded-full shrink-0 ${col.dot}`} />
        <div className="flex-1 min-w-0">
          {finding.excerpt && (
            <p className="text-sm font-medium text-slate-800 dark:text-slate-100 truncate">
              &ldquo;{finding.excerpt}&rdquo;
            </p>
          )}
          <div className="flex items-center gap-2 mt-0.5">
            <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${col.badge}`}>{sevLabel}</span>
            {finding.category && (
              <span className="text-xs text-slate-400">{finding.category}</span>
            )}
          </div>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" /> : <ChevronDown className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />}
      </button>
      {open && (
        <div className="px-4 pb-3 space-y-2 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20 pt-2">
          {finding.explanation && (
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">{finding.explanation}</p>
          )}
          {finding.suggestion && (
            <div className="flex items-start gap-2 p-2 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-100 dark:border-green-900/40">
              <span className="text-xs font-semibold text-green-700 dark:text-green-400 shrink-0">
                {isHe ? 'הצעה:' : 'Suggestion:'}
              </span>
              <span className="text-xs text-green-700 dark:text-green-300">{finding.suggestion}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Detail modal ───────────────────────────────────────────────────────────

function DetailModal({ runId, locale, onClose }: { runId: string; locale: string; onClose: () => void }) {
  const isHe = locale === 'he';
  const [detail, setDetail] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    getAnalysisDetail(runId)
      .then(setDetail)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [runId]);

  const score = detail ? computeScore(detail.findings.length) : 100;
  const label = detail ? docLabel(detail, locale) : '';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl flex flex-col max-h-[85vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center gap-3 p-5 border-b border-slate-100 dark:border-slate-800 shrink-0">
          {detail && <ScoreRing score={score} size={48} />}
          <div className="flex-1 min-w-0">
            <h2 className="font-bold text-slate-900 dark:text-slate-100 truncate text-base">
              {label || (isHe ? 'טוען...' : 'Loading...')}
            </h2>
            {detail && (
              <div className="flex flex-wrap items-center gap-2 mt-0.5">
                <span className="text-xs text-slate-500 flex items-center gap-1">
                  <Clock className="w-3 h-3" />{formatDate(detail.analyzed_at, locale)}
                </span>
                {detail.page_count != null && detail.page_count > 0 && (
                  <span className="text-xs text-slate-500 flex items-center gap-1">
                    <BookOpen className="w-3 h-3" />{detail.page_count} {isHe ? 'עמ׳' : 'pp.'}
                  </span>
                )}
                {detail.language && (
                  <span className="text-xs text-slate-500 uppercase flex items-center gap-1">
                    <Globe className="w-3 h-3" />{detail.language}
                  </span>
                )}
                <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${scoreBg(score)} ${scoreRingColor(score)}`}>
                  {scoreLabel(score, locale)}
                </span>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition-colors shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          {loading && (
            <div className="flex justify-center py-10">
              <Loader2 className="w-7 h-7 animate-spin text-pride-purple" />
            </div>
          )}
          {error && (
            <p className="text-center text-red-500 text-sm py-10">
              {isHe ? 'שגיאה בטעינת הניתוח' : 'Failed to load analysis'}
            </p>
          )}
          {detail && !loading && (
            <>
              {detail.findings.length === 0 ? (
                <div className="flex flex-col items-center py-8 text-center">
                  <CheckCircle2 className="w-12 h-12 text-green-500 mb-3" />
                  <p className="font-semibold text-green-600 dark:text-green-400">
                    {isHe ? 'לא נמצאו בעיות' : 'No issues found'}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {isHe ? 'המסמך עבר ניתוח בהצלחה ללא ממצאים' : 'Document passed analysis with no flagged language'}
                  </p>
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                      {isHe ? `${detail.findings.length} ממצאים` : `${detail.findings.length} findings`}
                    </p>
                  </div>
                  {detail.findings.map(f => (
                    <FindingRow key={f.finding_id} finding={f} locale={locale} />
                  ))}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Analysis card ──────────────────────────────────────────────────────────

function AnalysisCard({
  entry, locale, onView, onDelete,
}: {
  entry: HistoryEntry; locale: string; onView: () => void; onDelete: () => void;
}) {
  const score = computeScore(entry.findings_count);
  const label = docLabel(entry, locale);
  const isHe = locale === 'he';

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete();
  };

  const severityBars = [
    { key: 'high', count: entry.findings_high, label: isHe ? 'גבוה' : 'High', color: 'bg-red-400' },
    { key: 'medium', count: entry.findings_medium, label: isHe ? 'בינוני' : 'Medium', color: 'bg-amber-400' },
    { key: 'low', count: entry.findings_low, label: isHe ? 'נמוך' : 'Low', color: 'bg-blue-400' },
  ];

  return (
    <div
      onClick={onView}
      className="w-full text-left rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 hover:border-pride-purple/40 hover:shadow-sm transition-all duration-150 group cursor-pointer"
    >
      <div className="flex items-start gap-4">
        <ScoreRing score={score} />

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p className="font-semibold text-slate-900 dark:text-slate-100 truncate leading-snug" title={label}>
              {label}
            </p>

            {/* Actions */}
            <div className="flex items-center gap-1 shrink-0" onClick={e => e.stopPropagation()}>
              <button
                onClick={handleDelete}
                title={isHe ? 'מחק' : 'Delete'}
                className="p-1.5 rounded-lg transition-colors text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 mt-1.5">
            <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
              <Clock className="w-3 h-3" />{formatDate(entry.analyzed_at, locale)}
            </span>
            {entry.page_count != null && entry.page_count > 0 && (
              <>
                <span className="text-xs text-slate-400">·</span>
                <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                  <BookOpen className="w-3 h-3" />{entry.page_count} {isHe ? 'עמ׳' : 'pp.'}
                </span>
              </>
            )}
            {entry.language && (
              <>
                <span className="text-xs text-slate-400">·</span>
                <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1 uppercase">
                  <Globe className="w-3 h-3" />{entry.language}
                </span>
              </>
            )}
            <span className="text-xs text-slate-400">·</span>
            <span className={`text-xs font-medium px-1.5 py-0.5 rounded-full ${scoreBg(score)} ${scoreRingColor(score)}`}>
              {scoreLabel(score, locale)}
            </span>
          </div>

          {entry.findings_count > 0 ? (
            <div className="mt-3 flex items-center gap-3">
              {severityBars.map(({ key, count, label: sLabel, color }) =>
                count > 0 ? (
                  <span key={key} className="flex items-center gap-1 text-xs text-slate-600 dark:text-slate-400">
                    <span className={`inline-block w-2 h-2 rounded-full ${color}`} />
                    {count} {sLabel}
                  </span>
                ) : null
              )}
            </div>
          ) : (
            <p className="mt-2 text-xs text-green-600 dark:text-green-400 font-medium">
              {isHe ? 'לא נמצאו בעיות' : 'No issues found'}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Empty state ────────────────────────────────────────────────────────────

function EmptyState({ locale }: { locale: string }) {
  const isHe = locale === 'he';
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="p-5 bg-slate-100 dark:bg-slate-800 rounded-full mb-5">
        <History className="w-10 h-10 text-slate-400" />
      </div>
      <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 mb-2">
        {isHe ? 'עדיין אין ניתוחים' : 'No analyses yet'}
      </h2>
      <p className="text-slate-500 dark:text-slate-400 text-sm max-w-xs mb-6">
        {isHe
          ? 'לאחר שתנתחו מסמך, הוא יופיע כאן עם כל התוצאות.'
          : 'Once you analyze a document, it will appear here with all results.'}
      </p>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────

export default function HistoryPage() {
  const params = useParams();
  const locale = (params?.locale as string) ?? 'en';
  const isHe = locale === 'he';

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [kpis, setKpis] = useState<HistoryKPIs | null>(null);
  const [analyses, setAnalyses] = useState<HistoryEntry[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    getHistory()
      .then((data) => {
        setKpis(data.kpis);
        setAnalyses(data.analyses);
      })
      .catch((err) => {
        if (err.message !== 'Session expired') {
          setError(isHe ? 'לא ניתן לטעון את ההיסטוריה. נסה שוב.' : 'Could not load history. Please try again.');
        }
      })
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = useCallback(async (runId: string) => {
    try {
      await deleteAnalysis(runId);
      setAnalyses(prev => prev.filter(a => a.run_id !== runId));
      setKpis(prev => prev ? { ...prev, total_analyses: prev.total_analyses - 1 } : prev);
    } catch {
      // silent — entry stays in list
    }
  }, []);

  const avgScore = analyses.length
    ? Math.round(analyses.reduce((s, a) => s + computeScore(a.findings_count), 0) / analyses.length)
    : 100;

  const cleanCount = analyses.filter(a => a.findings_count === 0).length;

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-pride-purple" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center py-20 text-center">
        <div>
          <p className="text-red-500 font-medium mb-3">{error}</p>
          <button onClick={load} className="text-sm text-pride-purple hover:underline">
            {isHe ? 'נסה שוב' : 'Try again'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      {activeRunId && (
        <DetailModal
          runId={activeRunId}
          locale={locale}
          onClose={() => setActiveRunId(null)}
        />
      )}

      <div className="flex-1 max-w-4xl mx-auto w-full px-4 py-8" dir={isHe ? 'rtl' : 'ltr'}>
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">
            {isHe ? 'הניתוחים שלי' : 'My Analyses'}
          </h1>
          <p className="mt-1 text-slate-500 dark:text-slate-400 text-sm">
            {isHe
              ? 'סקירה של כל הניתוחים שביצעת עם ציונים ותובנות'
              : 'Overview of all your analyses with scores and insights'}
          </p>
        </div>

        {/* KPI cards */}
        {kpis && kpis.total_analyses > 0 && (
          <div className="grid grid-cols-2 gap-3 mb-8 sm:grid-cols-4">
            <KpiCard
              icon={<FileText className="w-5 h-5 text-pride-purple" />}
              label={isHe ? 'סה״כ ניתוחים' : 'Total Analyses'}
              value={kpis.total_analyses}
              accent="bg-pride-purple/10"
            />
            <KpiCard
              icon={<TrendingUp className="w-5 h-5 text-blue-500" />}
              label={isHe ? 'ציון ממוצע' : 'Avg. Score'}
              value={avgScore}
              sub={scoreLabel(avgScore, locale)}
              accent="bg-blue-50 dark:bg-blue-950/30"
            />
            <KpiCard
              icon={<AlertTriangle className="w-5 h-5 text-amber-500" />}
              label={isHe ? 'סה״כ ממצאים' : 'Total Findings'}
              value={kpis.total_findings}
              sub={isHe ? `ממוצע ${kpis.avg_issues_per_doc} למסמך` : `avg ${kpis.avg_issues_per_doc} / doc`}
              accent="bg-amber-50 dark:bg-amber-950/30"
            />
            <KpiCard
              icon={<History className="w-5 h-5 text-green-500" />}
              label={isHe ? 'ניתוחים נקיים' : 'Clean Analyses'}
              value={`${cleanCount} / ${kpis.total_analyses}`}
              sub={isHe ? 'ללא ממצאים' : 'no issues found'}
              accent="bg-green-50 dark:bg-green-950/30"
            />
          </div>
        )}

        {/* Severity bar */}
        {kpis && kpis.total_findings > 0 && (
          <div className="mb-8 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
              {isHe ? 'פירוט ממצאים לפי חומרה' : 'Findings by severity'}
            </p>
            <div className="flex gap-2 h-3 rounded-full overflow-hidden mb-3">
              {kpis.findings_high > 0 && (
                <div className="bg-red-400 transition-all" style={{ width: `${(kpis.findings_high / kpis.total_findings) * 100}%` }} />
              )}
              {kpis.findings_medium > 0 && (
                <div className="bg-amber-400 transition-all" style={{ width: `${(kpis.findings_medium / kpis.total_findings) * 100}%` }} />
              )}
              {kpis.findings_low > 0 && (
                <div className="bg-blue-400 transition-all" style={{ width: `${(kpis.findings_low / kpis.total_findings) * 100}%` }} />
              )}
            </div>
            <div className="flex flex-wrap gap-4 text-xs text-slate-600 dark:text-slate-400">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-400 inline-block" />
                {isHe ? 'גבוה' : 'High'}: {kpis.findings_high}
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />
                {isHe ? 'בינוני' : 'Medium'}: {kpis.findings_medium}
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-blue-400 inline-block" />
                {isHe ? 'נמוך' : 'Low'}: {kpis.findings_low}
              </span>
            </div>
          </div>
        )}

        {/* List */}
        {analyses.length === 0 ? (
          <EmptyState locale={locale} />
        ) : (
          <div className="space-y-3">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
              {isHe ? `${analyses.length} ניתוחים אחרונים` : `${analyses.length} recent analyses`}
            </p>
            {analyses.map(entry => (
              <AnalysisCard
                key={entry.run_id}
                entry={entry}
                locale={locale}
                onView={() => setActiveRunId(entry.run_id)}
                onDelete={() => handleDelete(entry.run_id)}
              />
            ))}
          </div>
        )}
      </div>
    </>
  );
}
