import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import PrivateModeToggle from './PrivateModeToggle';

// Mock next-intl
jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => {
    const translations: Record<string, string> = {
      'privateMode.label': 'Private mode',
      'privateMode.tooltip': 'Your document will not be stored',
    };
    return translations[key] || key;
  },
}));

describe('PrivateModeToggle', () => {
  it('renders toggle with label', () => {
    render(<PrivateModeToggle checked={false} onCheckedChange={() => {}} />);
    expect(screen.getByRole('switch')).toBeInTheDocument();
    expect(screen.getByText('Private mode')).toBeInTheDocument();
  });

  it('calls onCheckedChange when clicked', () => {
    const handleChange = jest.fn();
    render(<PrivateModeToggle checked={false} onCheckedChange={handleChange} />);
    fireEvent.click(screen.getByRole('switch'));
    expect(handleChange).toHaveBeenCalledWith(true);
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <PrivateModeToggle checked={false} onCheckedChange={() => {}} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
