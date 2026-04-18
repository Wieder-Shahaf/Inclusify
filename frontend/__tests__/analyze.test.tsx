import React from 'react';
import { render, screen, act } from '@testing-library/react';

// Mock next-intl
jest.mock('next-intl', () => ({
  useTranslations: () => (k: string) => k,
  useLocale: () => 'en',
}));

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  useParams: () => ({ locale: 'en' }),
  usePathname: () => '/en/analyze',
}));

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
    button: ({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }) => <button {...props}>{children}</button>,
    h1: ({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }) => <h1 {...props}>{children}</h1>,
    p: ({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }) => <p {...props}>{children}</p>,
  },
  AnimatePresence: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}));

// Mock AuthContext
jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    getToken: () => 'test-token',
    refreshProfile: jest.fn(),
  }),
}));

// Mock LiveAnnouncerContext
jest.mock('@/contexts/LiveAnnouncerContext', () => ({
  useLiveAnnouncer: () => ({
    announce: jest.fn(),
  }),
}));

// Mock useKeyboardNavigation
jest.mock('@/hooks/useKeyboardNavigation', () => ({
  useKeyboardNavigation: () => {},
}));

// Mock exportReport
jest.mock('@/lib/exportReport', () => ({
  exportReport: jest.fn(),
}));

// Mock API calls
const mockUploadFile = jest.fn();
const mockAnalyzeText = jest.fn();
const mockHealthCheck = jest.fn().mockResolvedValue(true);
const mockModelHealthCheck = jest.fn().mockResolvedValue({ available: true });

jest.mock('@/lib/api/client', () => ({
  uploadFile: (...args: unknown[]) => mockUploadFile(...args),
  analyzeText: (...args: unknown[]) => mockAnalyzeText(...args),
  healthCheck: (...args: unknown[]) => mockHealthCheck(...args),
  modelHealthCheck: (...args: unknown[]) => mockModelHealthCheck(...args),
}));

// Default mock responses
const mockUploadResponse = {
  text: 'Sample academic text about gay individuals.',
  filename: 'test.pdf',
  mimeType: 'application/pdf',
  inputType: 'pdf',
  pageCount: 1,
  title: 'Test Paper',
  author: 'Test Author',
  detectedLanguage: 'en',
  fileStorageRef: null,
  chunks: [],
};

const mockAnalyzeResponseRulesOnly = {
  annotations: [],
  results: [],
  counts: { outdated: 0, biased: 0, potentially_offensive: 0, factually_incorrect: 0 },
  analysisMode: 'rules_only',
};

const mockAnalyzeResponseHybrid = {
  annotations: [],
  results: [],
  counts: { outdated: 0, biased: 0, potentially_offensive: 0, factually_incorrect: 0 },
  analysisMode: 'hybrid',
};

import AnalyzePage from '@/app/[locale]/analyze/page';

describe('AnalyzePage — LLM-down banner (D-02)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockHealthCheck.mockResolvedValue(true);
    mockModelHealthCheck.mockResolvedValue({ available: true });
    mockUploadFile.mockResolvedValue(mockUploadResponse);
  });

  it('renders HealthWarningBanner when analysisMode is rules_only in results view', async () => {
    mockAnalyzeText.mockResolvedValue(mockAnalyzeResponseRulesOnly);

    render(<AnalyzePage />);

    // Trigger file upload to transition to results state
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]');
    if (input) {
      await act(async () => {
        Object.defineProperty(input, 'files', { value: [file], configurable: true });
        input.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }

    // Wait for the async state transitions (upload + analyze)
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    // Assert: the llm-down results banner is present in the DOM
    const banner = screen.getByText(/llmDownResults/i);
    expect(banner).toBeInTheDocument();
    const link = screen.getByRole('link', { name: /llmDownResultsLink/i });
    expect(link).toHaveAttribute('href', expect.stringMatching(/\/en\/glossary$/));
  });

  it('does NOT render rules_only banner when analysisMode is hybrid', async () => {
    mockAnalyzeText.mockResolvedValue(mockAnalyzeResponseHybrid);

    render(<AnalyzePage />);

    // Trigger file upload to transition to results state
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]');
    if (input) {
      await act(async () => {
        Object.defineProperty(input, 'files', { value: [file], configurable: true });
        input.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }

    // Wait for the async state transitions
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 100));
    });

    // Assert: the rules_only banner is NOT rendered
    expect(screen.queryByText(/llmDownResults/i)).toBeNull();
  });
});
