import SeverityBadge, { Severity } from './SeverityBadge';

export type SeverityLevel = 'low' | 'medium' | 'high' | 'critical';

export type Result = {
  phrase: string;
  severity: Severity;
  severityLevel?: SeverityLevel;
  explanation: string;
  suggestion?: string;
  references?: Array<{ label: string; url: string }>;
};

export default function ResultCard({ r, bgColor }: { r: Result; bgColor?: string }) {
  return (
    <div className="glass rounded-xl p-4 border" style={bgColor ? { backgroundColor: bgColor } : undefined}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="font-semibold">{r.phrase}</div>
        <SeverityBadge level={r.severity} />
      </div>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{r.explanation}</p>
      {r.suggestion && (
        <p className="mt-2 text-sm">
          <span className="font-medium">Suggestion:</span> {r.suggestion}
        </p>
      )}
      {r.references?.length ? (
        <div className="mt-2 flex flex-wrap gap-3 text-xs">
          {r.references.map((ref, i) => (
            <a
              key={i}
              href={ref.url}
              target="_blank"
              rel="noreferrer"
              className="text-pride-purple hover:underline"
            >
              {ref.label}
            </a>
          ))}
        </div>
      ) : null}
    </div>
  );
}
