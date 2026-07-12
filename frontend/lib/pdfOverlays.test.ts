import { computeBboxOverlays } from './pdfOverlays';
import type { Annotation } from '@/components/AnnotatedText';
import type { BboxAnnotation } from '@/lib/api/client';

const ann = (start: number, end: number): Annotation => ({
  start,
  end,
  severity: 'biased',
  label: 'phrase',
});

describe('computeBboxOverlays', () => {
  // 500×1000pt page rendered at 1000px → scale 2
  const pageSizes = { '1': { width: 500, height: 1000 }, '2': { width: 500, height: 1000 } };
  const blocks: BboxAnnotation[] = [
    // chars 10–50, bottom-left origin: t=800 from page bottom → 200pt from top
    { start: 10, end: 50, page: 1, bbox: { l: 50, t: 800, r: 250, b: 760, coord_origin: 'BOTTOMLEFT' } },
    { start: 50, end: 90, page: 2, bbox: { l: 50, t: 900, r: 250, b: 860, coord_origin: 'BOTTOMLEFT' } },
  ];

  it('maps an overlapping annotation to a scaled, y-flipped overlay', () => {
    const map = computeBboxOverlays([ann(20, 30)], blocks, pageSizes, 1000);
    expect(map.get(1)).toHaveLength(1);
    expect(map.get(1)![0]).toMatchObject({ top: 400, left: 100, width: 400, height: 80 });
    expect(map.has(2)).toBe(false);
  });

  it('spans multiple blocks across pages', () => {
    const map = computeBboxOverlays([ann(40, 60)], blocks, pageSizes, 1000);
    expect(map.get(1)).toHaveLength(1);
    expect(map.get(2)).toHaveLength(1);
  });

  it('ignores annotations touching no block', () => {
    // [90, 95) starts exactly at block 2's exclusive end — no overlap
    expect(computeBboxOverlays([ann(90, 95)], blocks, pageSizes, 1000).size).toBe(0);
  });

  it('handles top-left origin without flipping', () => {
    const tl: BboxAnnotation[] = [
      { start: 10, end: 50, page: 1, bbox: { l: 50, t: 200, r: 250, b: 240, coord_origin: 'TOPLEFT' } },
    ];
    const map = computeBboxOverlays([ann(20, 30)], tl, pageSizes, 1000);
    expect(map.get(1)![0]).toMatchObject({ top: 400, height: 80 });
  });

  it('defaults to bottom-left when coord_origin is missing', () => {
    const noOrigin: BboxAnnotation[] = [
      { start: 10, end: 50, page: 1, bbox: { l: 50, t: 800, r: 250, b: 760 } },
    ];
    expect(computeBboxOverlays([ann(20, 30)], noOrigin, pageSizes, 1000).get(1)![0].top).toBe(400);
  });

  it('returns empty for missing bbox data or unknown pages', () => {
    expect(computeBboxOverlays([ann(20, 30)], null, pageSizes, 1000).size).toBe(0);
    expect(computeBboxOverlays([ann(20, 30)], blocks, null, 1000).size).toBe(0);
    const badPage: BboxAnnotation[] = [{ ...blocks[0], page: 7 }];
    expect(computeBboxOverlays([ann(20, 30)], badPage, pageSizes, 1000).size).toBe(0);
  });
});
