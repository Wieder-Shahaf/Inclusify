'use client';

import { useCallback, useEffect, RefObject } from 'react';
import { useLocale } from 'next-intl';

interface UseKeyboardNavigationOptions {
  containerRef: RefObject<HTMLElement | null>;
  itemSelector: string;
  enabled?: boolean;
  onSelect?: (element: HTMLElement, index: number) => void;
}

export function useKeyboardNavigation({
  containerRef,
  itemSelector,
  enabled = true,
  onSelect,
}: UseKeyboardNavigationOptions) {
  const locale = useLocale();
  const isRTL = locale === 'he';

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled || !containerRef.current) return;

      const items = Array.from(
        containerRef.current.querySelectorAll<HTMLElement>(itemSelector)
      );
      if (items.length === 0) return;

      const currentIndex = items.findIndex(
        (el) => el === document.activeElement || el.contains(document.activeElement)
      );

      let nextIndex = currentIndex;

      // RTL-aware arrow key mapping:
      // In LTR: Right = next, Left = previous
      // In RTL: Right = previous, Left = next (flipped)
      switch (e.key) {
        case 'ArrowRight':
          nextIndex = isRTL ? currentIndex - 1 : currentIndex + 1;
          break;
        case 'ArrowLeft':
          nextIndex = isRTL ? currentIndex + 1 : currentIndex - 1;
          break;
        case 'ArrowDown':
          nextIndex = currentIndex + 1;
          break;
        case 'ArrowUp':
          nextIndex = currentIndex - 1;
          break;
        case 'Home':
          nextIndex = 0;
          break;
        case 'End':
          nextIndex = items.length - 1;
          break;
        default:
          return; // Don't prevent default for other keys
      }

      // Wrap around
      if (nextIndex < 0) nextIndex = items.length - 1;
      if (nextIndex >= items.length) nextIndex = 0;

      // Only act if we have a valid target different from current
      if (nextIndex !== currentIndex || currentIndex === -1) {
        e.preventDefault();
        const targetElement = items[nextIndex];
        targetElement.focus();
        onSelect?.(targetElement, nextIndex);
      }
    },
    [containerRef, itemSelector, enabled, isRTL, onSelect]
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !enabled) return;

    container.addEventListener('keydown', handleKeyDown);
    return () => container.removeEventListener('keydown', handleKeyDown);
  }, [containerRef, enabled, handleKeyDown]);
}
