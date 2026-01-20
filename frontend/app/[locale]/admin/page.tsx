import { getTranslations } from 'next-intl/server';
import KpiCard from '@/components/dashboard/KpiCard';
import SimpleLineChart from '@/components/dashboard/SimpleLineChart';
import DonutChart from '@/components/dashboard/DonutChart';
import { paletteColor } from '@/lib/utils/palette';

export default async function AdminPage() {
  const t = await getTranslations();

  const kpis = [
    {
      label: t('admin.kpi.totalAnalyses'),
      value: '247',
      change: { value: 12, since: t('admin.kpi.since') },
      accent: 'sky' as const,
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
          <path d="M5 3h14a2 2 0 012 2v12a4 4 0 01-4 4H7a4 4 0 01-4-4V5a2 2 0 012-2zm2 4v2h10V7H7zm0 4v2h7v-2H7z" />
        </svg>
      ),
    },
    {
      label: t('admin.kpi.issuesFound'),
      value: '1,829',
      change: { value: -8, since: t('admin.kpi.since') },
      accent: 'amber' as const,
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
          <path d="M10.29 3.86l-8 14A1 1 0 003 19h16a1 1 0 00.86-1.5l-8-14a1 1 0 00-1.72 0zM12 9v4m0 4h.01" />
        </svg>
      ),
    },
    {
      label: t('admin.kpi.resolved'),
      value: '1,654',
      change: { value: 15, since: t('admin.kpi.since') },
      accent: 'green' as const,
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
          <path d="M9 12l2 2 4-5 2 2-6 7-4-4 2-2z" />
        </svg>
      ),
    },
    {
      label: t('admin.kpi.avgScore'),
      value: '82%',
      change: { value: 5, since: t('admin.kpi.since') },
      accent: 'purple' as const,
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
          <path d="M4 4h4v16H4V4zm6 6h4v10h-4V10zm6-4h4v14h-4V6z" />
        </svg>
      ),
    },
  ];

  const trendData = [68, 70, 69, 73, 76, 80, 77, 82, 81, 85, 84, 88];
  const trendLabels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  const issues = [
    { label: 'Outdated', value: 45, color: '#3b82f6' },
    { label: 'Biased', value: 30, color: '#f59e0b' },
    { label: 'Offensive', value: 15, color: '#ef4444' },
    { label: 'Incorrect', value: 10, color: '#8b5cf6' },
  ];

  const languages = [
    { lang: t('admin.languages.en'), runs: 142 },
    { lang: t('admin.languages.he'), runs: 95 },
  ];

  const topTerms = [
    { term: 'homosexual', count: 123, suggestion: 'gay/lesbian' },
    { term: 'sexual preference', count: 94, suggestion: 'sexual orientation' },
    { term: 'transsexual', count: 71, suggestion: 'transgender person' },
    { term: 'born as a man', count: 38, suggestion: 'assigned male at birth' },
  ];

  return (
    <div className="py-3 h-[calc(100vh-120px)] flex flex-col gap-3 overflow-hidden">
      {/* KPI Cards Row */}
      <div className="grid gap-3 grid-cols-2 xl:grid-cols-4 flex-shrink-0">
        {kpis.map((k, i) => (
          <KpiCard
            key={i}
            label={k.label}
            value={k.value}
            change={k.change}
            accent={k.accent}
            icon={k.icon}
            bgColor={paletteColor(i)}
            compact
          />
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid gap-3 xl:grid-cols-3 flex-1 min-h-0">
        <section
          className="xl:col-span-2 rounded-xl border glass p-3 flex flex-col"
          style={{ backgroundColor: paletteColor(4) }}
        >
          <div className="flex-shrink-0">
            <h3 className="text-sm font-semibold">{t('admin.scoreTrends')}</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">{t('admin.avgOverTime')}</p>
          </div>
          <div className="flex-1 mt-2 min-h-0">
            <SimpleLineChart data={trendData} labels={trendLabels} color="#7b61ff" />
          </div>
        </section>
        <section
          className="rounded-xl border glass p-3 flex flex-col"
          style={{ backgroundColor: paletteColor(1) }}
        >
          <div className="flex-shrink-0">
            <h3 className="text-sm font-semibold">{t('admin.issuesBreakdown')}</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">{t('admin.shareByCategory')}</p>
          </div>
          <div className="flex-1 flex items-center justify-center gap-4 min-h-0">
            <DonutChart
              data={issues}
              size={140}
              thickness={14}
              center={{
                title: '1,829',
                subtitle: t('admin.issuesFoundShort'),
                titleClassName: 'text-base font-extrabold',
                subtitleClassName: 'text-[9px] text-slate-500 dark:text-slate-400',
              }}
            />
            <div className="grid gap-1.5 text-xs">
              {issues.map((d, i) => (
                <div key={i} className="flex items-center gap-1.5">
                  <span
                    className="h-2.5 w-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: d.color }}
                  ></span>
                  <span className="whitespace-nowrap">
                    {d.label} <span className="font-semibold">{d.value}%</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>

      {/* Bottom Row */}
      <div className="grid gap-3 lg:grid-cols-3 flex-1 min-h-0">
        <section
          className="rounded-xl border glass p-3 lg:col-span-2 flex flex-col"
          style={{ backgroundColor: paletteColor(2) }}
        >
          <h3 className="text-sm font-semibold flex-shrink-0">{t('admin.topTerms')}</h3>
          <div className="mt-2 overflow-auto flex-1 min-h-0">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-slate-500 dark:text-slate-400">
                  <th className="py-1.5 pr-3">{t('admin.table.term')}</th>
                  <th className="py-1.5 pr-3">{t('admin.table.occurrences')}</th>
                  <th className="py-1.5">{t('admin.table.suggestion')}</th>
                </tr>
              </thead>
              <tbody>
                {topTerms.map((r, i) => (
                  <tr
                    key={i}
                    className="border-t border-slate-200/60 dark:border-slate-800/60"
                  >
                    <td className="py-1.5 pr-3 font-medium">{r.term}</td>
                    <td className="py-1.5 pr-3">{r.count}</td>
                    <td className="py-1.5">{r.suggestion}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section
          className="rounded-xl border glass p-3 flex flex-col"
          style={{ backgroundColor: paletteColor(0) }}
        >
          <h3 className="text-sm font-semibold flex-shrink-0">{t('admin.usageByLanguage')}</h3>
          <div className="mt-2 grid gap-3 flex-1 content-center">
            {languages.map((l, i) => (
              <div key={i}>
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium">{l.lang}</span>
                  <span className="text-slate-500 dark:text-slate-400">
                    {l.runs} {t('admin.runs')}
                  </span>
                </div>
                <div className="mt-1 h-2 w-full rounded-full bg-slate-900/5 dark:bg-white/5 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-pride-purple to-pride-pink"
                    style={{ width: `${(l.runs / 200) * 100}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
