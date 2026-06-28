'use client';

import { useState, useEffect } from 'react';

/**
 * SSR-safe viewport breakpoint hook.
 *
 * Returns `false` on the server and on the first client render, then updates
 * after mount based on `matchMedia`. Initializing to `false` (desktop) keeps
 * server output and the first hydration pass identical to the desktop tree,
 * so this never causes a hydration mismatch. Callers that mount heavy,
 * desktop-only subtrees should branch on this value so phones skip them.
 *
 * Default breakpoint is 1023px — i.e. anything below Tailwind's `lg`.
 */
export function useIsMobile(maxWidth = 1023): boolean {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const query = window.matchMedia(`(max-width: ${maxWidth}px)`);
    const update = () => setIsMobile(query.matches);

    update();
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, [maxWidth]);

  return isMobile;
}
