import { getTranslations, getLocale } from 'next-intl/server';
import Link from 'next/link';

export default async function HomePage() {
  const t = await getTranslations();
  const locale = await getLocale();

  const features = [
    {
      key: 'smartDetection',
      color: '#E5D9F2',
      emoji: '🧠',
    },
    {
      key: 'bilingualSupport',
      color: '#D1E9F6',
      emoji: '🌐',
    },
    {
      key: 'gradedAlerts',
      color: '#FFF8DE',
      emoji: '⚠️',
    },
    {
      key: 'exportableReports',
      color: '#E7FBBE',
      emoji: '📄',
    },
    {
      key: 'educationalResources',
      color: '#FFEAEA',
      emoji: '📖',
    },
    {
      key: 'privacyFirst',
      color: '#F5EFFF',
      emoji: '🔒',
    },
  ];

  const isHebrew = locale === 'he';

  return (
    <div className="h-[calc(100vh-130px)] flex flex-col">
      {/* Hero Section */}
      <section className="text-center py-8">
        <div className="mx-auto max-w-3xl">
          <h1
            className={`text-4xl md:text-5xl ${
              isHebrew ? 'font-light hebrew-hero' : 'font-black'
            } tracking-tight bg-gradient-to-tr from-pride-purple to-pride-pink bg-clip-text text-transparent`}
          >
            {isHebrew ? (
              <>
                <span className="block">{t('home.heroHeadlineTop')}</span>
                <span className="block">{t('home.heroHeadlineBottom')}</span>
              </>
            ) : (
              t('home.heroHeadline')
            )}
          </h1>
          <p className="mt-3 text-base md:text-lg text-slate-600 dark:text-slate-300">
            {isHebrew ? (
              <>
                <span className="brand-raleway text-pride-purple font-extrabold">INCLUSIFY</span>{' '}
                מאתרת ניסוחים בעייתיים ומציעה לכם נוסח חדש מקצועי ומכבד יותר - בלחיצת כפתור!
              </>
            ) : (
              t('home.heroSub')
            )}
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <Link href={`/${locale}/analyze`} className="btn-primary">
              {t('app.cta')}
            </Link>
            <Link href={`/${locale}/glossary`} className="btn-ghost">
              {t('app.glossary')}
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section - fills remaining space */}
      <section className="flex-1 grid grid-cols-2 xl:grid-cols-3 gap-4 pb-4">
        {features.map((f, i) => (
          <div
            key={i}
            className="rounded-2xl p-5 border shadow-soft-xl flex flex-col"
            style={{ backgroundColor: f.color }}
          >
            <div className="flex items-start gap-4">
              <div className="h-11 w-11 rounded-xl grid place-items-center text-2xl bg-white/70 flex-shrink-0">
                <span role="img" aria-label={f.key}>
                  {f.emoji}
                </span>
              </div>
              <div className="flex-1">
                <h3 className="text-base md:text-lg font-extrabold leading-tight">
                  {t(`home.featuresDetailed.${f.key}.title`)}
                </h3>
                <p className="mt-2 text-slate-700 dark:text-slate-300 text-sm leading-relaxed">
                  {t(`home.featuresDetailed.${f.key}.desc`)}
                </p>
              </div>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
