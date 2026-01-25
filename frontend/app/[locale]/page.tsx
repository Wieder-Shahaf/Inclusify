import { getTranslations, setRequestLocale } from 'next-intl/server';
import HeroSection from '@/components/landing/HeroSection';
import DemoPreview from '@/components/landing/DemoPreview';
import HowItWorks from '@/components/landing/HowItWorks';
import FeaturesGrid from '@/components/landing/FeaturesGrid';
import CTASection from '@/components/landing/CTASection';

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function HomePage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  const t = await getTranslations();
  const isHebrew = locale === 'he';

  const features = [
    {
      key: 'smartDetection',
      title: t('home.featuresDetailed.smartDetection.title'),
      description: t('home.featuresDetailed.smartDetection.desc'),
    },
    {
      key: 'bilingualSupport',
      title: t('home.featuresDetailed.bilingualSupport.title'),
      description: t('home.featuresDetailed.bilingualSupport.desc'),
    },
    {
      key: 'gradedAlerts',
      title: t('home.featuresDetailed.gradedAlerts.title'),
      description: t('home.featuresDetailed.gradedAlerts.desc'),
    },
    {
      key: 'exportableReports',
      title: t('home.featuresDetailed.exportableReports.title'),
      description: t('home.featuresDetailed.exportableReports.desc'),
    },
    {
      key: 'educationalResources',
      title: t('home.featuresDetailed.educationalResources.title'),
      description: t('home.featuresDetailed.educationalResources.desc'),
    },
    {
      key: 'privacyFirst',
      title: t('home.featuresDetailed.privacyFirst.title'),
      description: t('home.featuresDetailed.privacyFirst.desc'),
    },
  ];

  const heroTranslations = {
    headline: t('home.heroHeadline'),
    headlineTop: t('home.heroHeadlineTop'),
    headlineBottom: t('home.heroHeadlineBottom'),
    subheadline: t('home.heroSub'),
    cta: t('app.cta'),
    secondaryCta: t('app.glossary'),
    badge: t('home.heroBadge'),
    trustFree: t('home.trustFree'),
    trustNoSignup: t('home.trustNoSignup'),
    trustPrivacy: t('home.trustPrivacy'),
  };

  const demoTranslations = {
    title: t('home.demoTitle'),
    subtitle: t('home.demoSubtitle'),
    label: t('home.demoLabel'),
    issuesDetected: t('home.demoIssuesDetected'),
    demoText: t('home.demoText'),
    term1: t('home.demoTerm1'),
    suggestion1: t('home.demoSuggestion1'),
    term2: t('home.demoTerm2'),
    suggestion2: t('home.demoSuggestion2'),
    outdated: t('severity.outdated'),
    biased: t('severity.biased'),
  };

  const howItWorksTranslations = {
    title: t('home.howItWorksTitle'),
    subtitle: t('home.howItWorksSubtitle'),
    step1Title: t('home.step1Title'),
    step1Desc: t('home.step1Desc'),
    step2Title: t('home.step2Title'),
    step2Desc: t('home.step2Desc'),
    step3Title: t('home.step3Title'),
    step3Desc: t('home.step3Desc'),
  };

  const featuresGridTranslations = {
    title: t('home.featuresTitle'),
    subtitle: t('home.featuresSubtitle'),
  };

  const ctaTranslations = {
    title: t('home.ctaTitle'),
    subtitle: t('home.ctaSubtitle'),
    formats: t('home.ctaFormats'),
    instant: t('home.ctaInstant'),
    private: t('home.ctaPrivate'),
    cta: t('app.cta'),
  };

  return (
    <div className="flex flex-col">
      <HeroSection
        locale={locale}
        isHebrew={isHebrew}
        translations={heroTranslations}
      />

      <DemoPreview isHebrew={isHebrew} translations={demoTranslations} />

      <HowItWorks isHebrew={isHebrew} translations={howItWorksTranslations} />

      <FeaturesGrid features={features} translations={featuresGridTranslations} />

      <CTASection locale={locale} translations={ctaTranslations} />
    </div>
  );
}
