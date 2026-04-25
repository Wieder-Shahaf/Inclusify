/**
 * Tests for exportReport.ts
 * RED phase: These tests define the target behavior for:
 *   - returnBase64 mode (returns data URI string)
 *   - Locale-aware footer watermark (EN/HE)
 *   - Removal of diagonal INCLUSIFY watermark
 */

// Mock jspdf and jspdf-autotable before importing the module under test
const saveSpy = jest.fn();
const textSpy = jest.fn();
const setPageSpy = jest.fn();
const outputMock = jest.fn(() => 'data:application/pdf;base64,MOCK');
const setFontSizeSpy = jest.fn();
const setFontSpy = jest.fn();
const setTextColorSpy = jest.fn();
const getTextWidthSpy = jest.fn((text: string) => text.length * 1.8);
const splitTextToSizeSpy = jest.fn((text: string) => [text]);

jest.mock('jspdf', () => ({
  __esModule: true,
  jsPDF: jest.fn().mockImplementation(() => ({
    setFillColor: jest.fn(),
    rect: jest.fn(),
    circle: jest.fn(),
    line: jest.fn(),
    setDrawColor: jest.fn(),
    setLineWidth: jest.fn(),
    setTextColor: setTextColorSpy,
    setFontSize: setFontSizeSpy,
    setFont: setFontSpy,
    text: textSpy,
    setPage: setPageSpy,
    save: saveSpy,
    output: outputMock,
    addImage: jest.fn(),
    addPage: jest.fn(),
    getTextWidth: getTextWidthSpy,
    splitTextToSize: splitTextToSizeSpy,
    internal: {
      pageSize: {
        getWidth: () => 210,
        getHeight: () => 297,
      },
      getNumberOfPages: () => 1,
    },
    getNumberOfPages: () => 1,
  })),
}));

jest.mock('jspdf-autotable', () => ({
  __esModule: true,
  default: jest.fn(),
}));

import { exportReport } from '../lib/exportReport';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockAnalysis: any = {
  text: 'Sample text for analysis',
  annotations: [
    {
      label: 'test term',
      severity: 'low',
      explanation: 'test rationale',
      suggestion: 'test suggestion',
      inclusive_sentence: 'test rewrite',
      start: 0,
      end: 4,
    },
  ],
  counts: {
    outdated: 1,
    biased: 0,
    potentially_offensive: 0,
    factually_incorrect: 0,
  },
  summary: {
    totalIssues: 1,
    score: 85,
    recommendations: ['Consider using more inclusive language'],
  },
};

beforeEach(() => {
  saveSpy.mockClear();
  textSpy.mockClear();
  setPageSpy.mockClear();
  outputMock.mockClear();
  setFontSizeSpy.mockClear();
  setFontSpy.mockClear();
  setTextColorSpy.mockClear();
  getTextWidthSpy.mockClear();
  splitTextToSizeSpy.mockClear();
});

describe('exportReport', () => {
  it('returns a data URI string when returnBase64 is true', async () => {
    const result = await exportReport(mockAnalysis, {
      fileName: 'x',
      locale: 'en',
      returnBase64: true,
    });
    expect(typeof result).toBe('string');
    expect(result).toMatch(/^data:application\/pdf;base64,/);
  });

  it('returns undefined (void) when returnBase64 is false/undefined', async () => {
    const result = await exportReport(mockAnalysis, {
      fileName: 'x',
      locale: 'en',
    });
    expect(result).toBeUndefined();
  });

  it('does not call doc.save() when returnBase64 is true', async () => {
    await exportReport(mockAnalysis, {
      fileName: 'x',
      locale: 'en',
      returnBase64: true,
    });
    expect(saveSpy).not.toHaveBeenCalled();
  });

  it('calls doc.save() when returnBase64 is false/undefined', async () => {
    await exportReport(mockAnalysis, {
      fileName: 'testfile',
      locale: 'en',
    });
    expect(saveSpy).toHaveBeenCalledTimes(1);
    expect(saveSpy).toHaveBeenCalledWith(expect.stringMatching(/_inclusify_report\.pdf$/));
  });

  it('footer text for en locale contains "Achva LGBTQ+ Student Organization"', async () => {
    await exportReport(mockAnalysis, {
      fileName: 'x',
      locale: 'en',
      returnBase64: true,
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const allTextArgs = textSpy.mock.calls.map((call: any[]) => call[0]);
    expect(allTextArgs).toEqual(
      expect.arrayContaining([
        expect.stringContaining('Achva LGBTQ+ Student Organization'),
      ])
    );
  });

  it('uses the display score passed from the visible UI state', async () => {
    await exportReport(mockAnalysis, {
      fileName: 'x',
      locale: 'en',
      returnBase64: true,
      displayScore: 72,
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const allTextArgs = textSpy.mock.calls.map((call: any[]) => call[0]);
    expect(allTextArgs).toEqual(expect.arrayContaining(['72', '/100']));
    expect(allTextArgs).not.toEqual(expect.arrayContaining(['72%']));
  });

  it('footer text for he locale contains Hebrew watermark string', async () => {
    await exportReport(mockAnalysis, {
      fileName: 'x',
      locale: 'he',
      returnBase64: true,
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const allTextArgs = textSpy.mock.calls.map((call: any[]) => call[0]);
    expect(allTextArgs).toEqual(
      expect.arrayContaining([
        expect.stringContaining('ארגון אחווה להט״ב הסטודנטיאלי'),
      ])
    );
  });

  it('no diagonal watermark call with angle 45', async () => {
    await exportReport(mockAnalysis, {
      fileName: 'x',
      locale: 'en',
      returnBase64: true,
    });
    const diagonalCall = textSpy.mock.calls.find(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (call: any[]) => call[2] && typeof call[2] === 'object' && call[2].angle === 45
    );
    expect(diagonalCall).toBeUndefined();
  });

  it('doc.output is called with datauristring when returnBase64 is true', async () => {
    await exportReport(mockAnalysis, {
      fileName: 'x',
      locale: 'en',
      returnBase64: true,
    });
    expect(outputMock).toHaveBeenCalledWith('datauristring');
  });
});
