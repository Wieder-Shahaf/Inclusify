import React from 'react';
import { render, screen } from '@testing-library/react';
import HealthWarningBanner from '@/components/HealthWarningBanner';

// Mock next/link
jest.mock('next/link', () => {
  const MockLink = ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  );
  MockLink.displayName = 'MockLink';
  return MockLink;
});

// Mock framer-motion to avoid animation issues in tests
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}));

/**
 * Harness that reproduces the exact conditional from analyze/page.tsx:
 *   {viewState === 'results' && analysisMode === 'rules_only' && (
 *     <HealthWarningBanner
 *       message={t('llmDownResults')}
 *       variant="error"
 *       linkHref={`/${locale}/glossary`}
 *       linkText={t('llmDownResultsLink')}
 *     />
 *   )}
 *
 * Using Option B (thin harness) to avoid mocking the full page dependency graph.
 * The banner message and link text match what useTranslations('analyzer') returns
 * for the keys defined in en.json.
 */
function AnalyzeResultsBannerHarness({
  viewState,
  analysisMode,
  locale = 'en',
}: {
  viewState: 'upload' | 'processing' | 'results';
  analysisMode: string | null;
  locale?: string;
}) {
  // Reproduce the exact i18n strings from en.json
  const messages: Record<string, string> = {
    llmDownResults: 'Analysis service is temporarily unavailable. Browse the glossary for guidance.',
    llmDownResultsLink: 'Browse glossary',
  };
  const t = (k: string) => messages[k] ?? k;

  return (
    <div>
      {viewState === 'results' && analysisMode === 'rules_only' && (
        <HealthWarningBanner
          message={t('llmDownResults')}
          variant="error"
          linkHref={`/${locale}/glossary`}
          linkText={t('llmDownResultsLink')}
        />
      )}
    </div>
  );
}

describe('AnalyzePage — LLM-down banner (D-02)', () => {
  it('renders HealthWarningBanner when analysisMode is rules_only in results view', () => {
    render(
      <AnalyzeResultsBannerHarness viewState="results" analysisMode="rules_only" locale="en" />
    );

    // Assert: banner message is present in the DOM
    const banner = screen.getByText(/Analysis service is temporarily unavailable/i);
    expect(banner).toBeInTheDocument();

    // Assert: glossary link is present with correct href
    const link = screen.getByRole('link', { name: /Browse glossary/i });
    expect(link).toHaveAttribute('href', expect.stringMatching(/\/en\/glossary$/));
  });

  it('does NOT render rules_only banner when analysisMode is hybrid', () => {
    render(
      <AnalyzeResultsBannerHarness viewState="results" analysisMode="hybrid" locale="en" />
    );

    expect(screen.queryByText(/Analysis service is temporarily unavailable/i)).toBeNull();
  });

  it('does NOT render rules_only banner when viewState is upload (even with rules_only mode)', () => {
    render(
      <AnalyzeResultsBannerHarness viewState="upload" analysisMode="rules_only" locale="en" />
    );

    expect(screen.queryByText(/Analysis service is temporarily unavailable/i)).toBeNull();
  });

  it('does NOT render rules_only banner when viewState is processing', () => {
    render(
      <AnalyzeResultsBannerHarness viewState="processing" analysisMode="rules_only" locale="en" />
    );

    expect(screen.queryByText(/Analysis service is temporarily unavailable/i)).toBeNull();
  });
});
