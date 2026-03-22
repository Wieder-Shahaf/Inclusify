'use client';

import { useEffect, useState, useRef } from 'react';
import { cn } from '@/lib/utils';
import { Sun, Moon } from 'lucide-react';

const THEME_KEY = 'inclusify-theme';

export default function ThemeToggle() {
  const [dark, setDark] = useState<boolean | null>(null);
  const mountedRef = useRef(false);

  // Hydrate theme from localStorage after mount (avoids SSR mismatch)
  /* eslint-disable react-hooks/set-state-in-effect -- Must hydrate from localStorage post-mount to avoid SSR mismatch */
  useEffect(() => {
    mountedRef.current = true;
    const saved = localStorage.getItem(THEME_KEY);
    const isDark = saved === 'dark';
    setDark(isDark);

    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  // Update DOM and localStorage when theme changes
  useEffect(() => {
    if (!mountedRef.current || dark === null) return;

    const html = document.documentElement;
    if (dark) {
      html.classList.add('dark');
      localStorage.setItem(THEME_KEY, 'dark');
    } else {
      html.classList.remove('dark');
      localStorage.setItem(THEME_KEY, 'light');
    }
  }, [dark]);

  const toggleTheme = () => {
    setDark((d) => !d);
  };

  // Show a placeholder while hydrating to prevent flash
  if (dark === null) {
    return (
      <button
        className={cn("btn-ghost rounded-full p-2 w-9 h-9")}
        title="Toggle theme"
        aria-label="Toggle theme"
      >
        <span className="w-5 h-5 block" />
      </button>
    );
  }

  return (
    <button
      onClick={toggleTheme}
      className={cn(
        "btn-ghost rounded-full p-2 transition-all duration-200",
        "hover:bg-slate-100 dark:hover:bg-slate-800"
      )}
      aria-pressed={dark}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
    >
      <div className="relative w-5 h-5">
        {/* Sun Icon - shown in dark mode */}
        <Sun
          className={cn(
            "absolute inset-0 w-5 h-5 transition-all duration-300",
            dark
              ? "opacity-100 rotate-0 scale-100 text-yellow-400"
              : "opacity-0 -rotate-90 scale-50"
          )}
        />
        {/* Moon Icon - shown in light mode */}
        <Moon
          className={cn(
            "absolute inset-0 w-5 h-5 transition-all duration-300",
            dark
              ? "opacity-0 rotate-90 scale-50"
              : "opacity-100 rotate-0 scale-100 text-slate-600"
          )}
        />
      </div>
    </button>
  );
}
