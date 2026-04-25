'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';
import * as Dialog from '@radix-ui/react-dialog';
import { motion } from 'framer-motion';
import { X, CheckCircle } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { sendContactMessage } from '@/lib/api/contact';
import { exportReport } from '@/lib/exportReport';
import type { Annotation } from '@/components/AnnotatedText';
import type { Severity } from '@/components/SeverityBadge';

// Minimal subset of AnalysisData that exportReport needs
export interface AnalysisData {
  text: string;
  annotations: Annotation[];
  results?: Array<{
    phrase: string;
    severity: Severity;
    category?: string;
    explanation: string;
    suggestion?: string;
    references?: Array<{ label: string; url: string }>;
  }>;
  counts: Record<Severity, number>;
  summary: {
    totalIssues: number;
    score: number;
    recommendations: string[];
  };
}

interface ContactModalProps {
  open: boolean;
  onClose: () => void;
  analysis?: AnalysisData | null;
  fileName?: string;
  locale?: string;
}

const schema = z.object({
  subject: z.string().min(1, 'required').max(300),
  message: z.string().min(1, 'required').max(5000),
});

type FormData = z.infer<typeof schema>;

export default function ContactModal({ open, onClose, analysis, fileName, locale }: ContactModalProps) {
  const t = useTranslations('contact');
  const { user } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    try {
      let pdfBlob: Blob | undefined;
      if (analysis) {
        const dataUri = await exportReport(analysis, {
          fileName: fileName || 'analysis',
          locale,
          returnBase64: true,
        });
        if (typeof dataUri === 'string' && dataUri.includes(',')) {
          const base64 = dataUri.split(',')[1];
          const binary = atob(base64);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
          pdfBlob = new Blob([bytes], { type: 'application/pdf' });
        }
      }
      await sendContactMessage({
        subject: data.subject,
        message: data.message,
        senderName: user?.full_name || '',
        senderEmail: user?.email || '',
        senderInstitution: user?.institution || '',
        pdfBlob,
      });
      toast.success(t('success'));
      reset();
      onClose();
    } catch {
      toast.error(t('error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={(v) => { if (!v) onClose(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2 }}
            className="glass p-8 rounded-2xl shadow-2xl"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <Dialog.Title className="text-xl font-bold text-slate-900 dark:text-slate-100">
                  {t('title')}
                </Dialog.Title>
                <Dialog.Description className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  {t('subtitle')}
                </Dialog.Description>
              </div>
              <Dialog.Close aria-label="Close" className="text-slate-500 hover:text-slate-700">
                <X className="w-5 h-5" />
              </Dialog.Close>
            </div>

            {user && (
              <div className="space-y-2 mb-4">
                <div>
                  <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">
                    {t('nameLabel')}
                  </label>
                  <p className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-sm">
                    {user.full_name || '—'}
                  </p>
                </div>
                <div>
                  <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">
                    {t('emailLabel')}
                  </label>
                  <p className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-sm">
                    {user.email || '—'}
                  </p>
                </div>
                <div>
                  <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">
                    {t('institutionLabel')}
                  </label>
                  <p className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-sm">
                    {user.institution || '—'}
                  </p>
                </div>
              </div>
            )}

            {analysis && (
              <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400 mb-4">
                <CheckCircle className="w-4 h-4" />
                <span>{t('attachReport')}</span>
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('subject')}
                </label>
                <input
                  {...register('subject')}
                  aria-required="true"
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple"
                />
                {errors.subject && (
                  <p className="text-red-500 text-xs mt-1">{errors.subject.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('message')}
                </label>
                <textarea
                  {...register('message')}
                  aria-required="true"
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple min-h-24 resize-y"
                />
                {errors.message && (
                  <p className="text-red-500 text-xs mt-1">{errors.message.message}</p>
                )}
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={onClose}
                  className="btn-ghost flex-1"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? t('sending') : t('send')}
                </button>
              </div>
            </form>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
