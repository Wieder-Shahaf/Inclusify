'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { updateProfile } from '@/lib/api/auth';

const DISMISSED_KEY = 'profile_setup_dismissed';

export const profileSetupSchema = z.object({
  full_name: z.string().min(1, 'required').max(200),
  profession: z.string().min(1, 'required').max(200),
  institution: z.string().min(1, 'required').max(200),
});

const schema = profileSetupSchema;

type FormData = z.infer<typeof schema>;

export function ProfileSetupModal() {
  const t = useTranslations('profile.setup');
  const { user, getToken, refreshProfile } = useAuth();
  const [open, setOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  useEffect(() => {
    if (!user) return;
    const dismissed = sessionStorage.getItem(DISMISSED_KEY);
    if (!dismissed && (!user.full_name || !user.institution || !user.profession)) {
      setOpen(true);
    }
  }, [user]);

  const dismiss = () => {
    sessionStorage.setItem(DISMISSED_KEY, '1');
    setOpen(false);
  };

  const onSubmit = async (data: FormData) => {
    const token = getToken();
    if (!token) return;
    setIsSubmitting(true);
    try {
      await updateProfile(token, {
        full_name: data.full_name,
        profession: data.profession,
        institution: data.institution,
      });
      await refreshProfile();
      toast.success(t('success'));
      dismiss();
    } catch {
      toast.error(t('error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={(v) => { if (!v) dismiss(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm" />
        <Dialog.Content className="fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md">
          <div className="glass p-8 rounded-2xl shadow-2xl">
            <div className="flex items-start justify-between mb-6">
              <div>
                <Dialog.Title className="text-xl font-bold text-slate-900 dark:text-slate-100">
                  {t('title')}
                </Dialog.Title>
                <Dialog.Description className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  {t('subtitle')}
                </Dialog.Description>
              </div>
              <Dialog.Close asChild>
                <button
                  onClick={dismiss}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                  aria-label="Close"
                >
                  <X className="w-5 h-5" />
                </button>
              </Dialog.Close>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('fullName')} <span className="text-red-500">*</span>
                </label>
                <input
                  {...register('full_name')}
                  autoFocus
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple"
                  placeholder={t('fullNamePlaceholder')}
                />
                {errors.full_name && (
                  <p className="text-xs text-red-500 mt-1">{t('required')}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('profession')} <span className="text-red-500" aria-hidden="true">*</span>
                </label>
                <input
                  {...register('profession')}
                  aria-required="true"
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple"
                  placeholder={t('professionPlaceholder')}
                />
                {errors.profession && (
                  <p className="text-xs text-red-500 mt-1">{t('required')}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('institution')} <span className="text-red-500" aria-hidden="true">*</span>
                </label>
                <input
                  {...register('institution')}
                  aria-required="true"
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple"
                  placeholder={t('institutionPlaceholder')}
                />
                {errors.institution && (
                  <p className="text-xs text-red-500 mt-1">{t('required')}</p>
                )}
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? t('saving') : t('save')}
                </button>
                <button
                  type="button"
                  onClick={dismiss}
                  className="flex-1 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  {t('skip')}
                </button>
              </div>
            </form>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
