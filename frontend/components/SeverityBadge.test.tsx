import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';
import SeverityBadge from './SeverityBadge';

// Mock next-intl
jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      outdated: 'Outdated',
      biased: 'Biased',
      offensive: 'Offensive',
      incorrect: 'Incorrect',
    };
    return translations[key] || key;
  },
}));

describe('SeverityBadge', () => {
  const severities = ['outdated', 'biased', 'offensive', 'incorrect'] as const;

  severities.forEach((severity) => {
    it(`renders ${severity} badge correctly`, () => {
      render(<SeverityBadge level={severity} />);
      expect(screen.getByText(severity.charAt(0).toUpperCase() + severity.slice(1))).toBeInTheDocument();
    });
  });

  it('has no accessibility violations', async () => {
    const { container } = render(<SeverityBadge level="outdated" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('renders with different background colors for each severity', () => {
    const { rerender, container } = render(<SeverityBadge level="outdated" />);
    const outdatedBadge = container.querySelector('span');
    expect(outdatedBadge).toHaveClass('bg-sky-100');

    rerender(<SeverityBadge level="biased" />);
    const biasedBadge = container.querySelector('span');
    expect(biasedBadge).toHaveClass('bg-amber-100');

    rerender(<SeverityBadge level="offensive" />);
    const offensiveBadge = container.querySelector('span');
    expect(offensiveBadge).toHaveClass('bg-rose-100');

    rerender(<SeverityBadge level="incorrect" />);
    const incorrectBadge = container.querySelector('span');
    expect(incorrectBadge).toHaveClass('bg-red-100');
  });
});
