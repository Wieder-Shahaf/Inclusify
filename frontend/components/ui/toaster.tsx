'use client';

import { Toaster as SonnerToaster } from 'sonner';

export function Toaster() {
  return (
    <SonnerToaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        classNames: {
          toast: 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700',
          title: 'text-slate-900 dark:text-slate-100',
          description: 'text-slate-600 dark:text-slate-400',
          error: 'border-red-200 dark:border-red-800',
          success: 'border-green-200 dark:border-green-800',
        },
      }}
    />
  );
}
