// Lightweight guard for programmatic navigation (router.push/replace from
// buttons — e.g. the language switcher), which the analyze page's anchor-click
// interception can't see.
//
// While an analysis is running, the analyze page registers a guard. Components
// that navigate programmatically call guardedNavigate(proceed): if a guard is
// active it decides (shows the leave-confirmation dialog and calls `proceed`
// only if the user confirms); otherwise `proceed` runs immediately.

type Guard = (proceed: () => void) => void;

let activeGuard: Guard | null = null;

/** Register a navigation guard. Returns an unregister function. */
export function registerNavigationGuard(guard: Guard): () => void {
  activeGuard = guard;
  return () => {
    if (activeGuard === guard) activeGuard = null;
  };
}

/** Run a programmatic navigation through the active guard (if any). */
export function guardedNavigate(proceed: () => void): void {
  if (activeGuard) {
    activeGuard(proceed);
  } else {
    proceed();
  }
}
