import type { Annotation } from '@/components/AnnotatedText';
import type { BboxAnnotation, PageSize } from '@/lib/api/client';

export type PdfOverlay = {
  top: number;
  left: number;
  width: number;
  height: number;
  annotation: Annotation;
};

/**
 * Map annotation char-ranges to page overlay rects using the Docling
 * offset→bbox provenance index from ingestion. Annotation offsets and bbox
 * item offsets both index the same export_to_text() string, so this is a
 * pure interval-overlap + coordinate-scale — no text matching.
 *
 * bbox coords are PDF points; PDF provenance uses a bottom-left origin
 * (t > b, y measured from the page bottom) unless coord_origin says TOPLEFT.
 * Docling blocks are paragraph-level, so a highlight marks the containing block.
 */
export function computeBboxOverlays(
  annotations: Annotation[],
  bboxAnnotations: BboxAnnotation[] | null | undefined,
  pageSizes: Record<string, PageSize> | null | undefined,
  renderWidth: number,
): Map<number, PdfOverlay[]> {
  const byPage = new Map<number, PdfOverlay[]>();
  if (!bboxAnnotations?.length || !pageSizes) return byPage;

  for (const ann of annotations) {
    for (const item of bboxAnnotations) {
      if (item.end <= ann.start || item.start >= ann.end) continue;
      const size = pageSizes[String(item.page)];
      if (!size?.width || !size?.height) continue;

      const scale = renderWidth / size.width;
      const { l, t, r, b } = item.bbox;
      const topLeftOrigin = (item.bbox.coord_origin ?? 'BOTTOMLEFT').toUpperCase() === 'TOPLEFT';
      const top = (topLeftOrigin ? t : size.height - t) * scale;
      const width = (r - l) * scale;
      const height = Math.abs(t - b) * scale;
      if (width <= 0 || height <= 0) continue;

      const overlays = byPage.get(item.page) ?? [];
      overlays.push({ top, left: l * scale, width, height, annotation: ann });
      byPage.set(item.page, overlays);
    }
  }
  return byPage;
}
