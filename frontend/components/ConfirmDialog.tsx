'use client';

import * as Dialog from '@radix-ui/react-dialog';
import { AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel: string;
  /** 'danger' renders a red confirm button (deletes), 'default' purple */
  variant?: 'danger' | 'default';
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel,
  variant = 'default',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={(v) => { if (!v) onCancel(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-sm">
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 shadow-xl p-6">
            <div className="flex items-start gap-3">
              <div
                className={cn(
                  'p-2 rounded-full flex-shrink-0',
                  variant === 'danger'
                    ? 'bg-red-50 dark:bg-red-900/20'
                    : 'bg-pride-purple/10',
                )}
              >
                <AlertTriangle
                  className={cn(
                    'w-5 h-5',
                    variant === 'danger' ? 'text-red-500' : 'text-pride-purple',
                  )}
                />
              </div>
              <div className="min-w-0">
                <Dialog.Title className="text-base font-bold text-slate-900 dark:text-slate-100">
                  {title}
                </Dialog.Title>
                <Dialog.Description className="text-sm text-slate-500 dark:text-slate-400 mt-1.5 leading-relaxed">
                  {description}
                </Dialog.Description>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
              >
                {cancelLabel}
              </button>
              <button
                type="button"
                onClick={onConfirm}
                className={cn(
                  'px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors',
                  variant === 'danger'
                    ? 'bg-red-500 hover:bg-red-600'
                    : 'bg-pride-purple hover:bg-pride-purple/90',
                )}
              >
                {confirmLabel}
              </button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
