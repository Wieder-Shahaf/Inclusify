'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';
import { useAuth } from '@/contexts/AuthContext';
import { updateProfile } from '@/lib/api/auth';
import { AuthGuard } from '@/components/auth/AuthGuard';

const profileSchema = z.object({
  full_name: z.string().max(200).optional().or(z.literal('')),
  profession: z.string().max(200).optional().or(z.literal('')),
  institution: z.string().max(200).optional().or(z.literal('')),
});

type ProfileFormData = z.infer<typeof profileSchema>;

function ProfileForm() {
  const t = useTranslations('profile');
  const { user, getToken, refreshProfile } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { register, handleSubmit, reset, formState: { errors, isDirty } } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
  });

  useEffect(() => {
    if (user) {
      reset({
        full_name: user.full_name ?? '',
        profession: user.profession ?? '',
        institution: user.institution ?? '',
      });
    }
  }, [user, reset]);

  const onSubmit = async (data: ProfileFormData) => {
    const token = getToken();
    if (!token) return;
    setIsSubmitting(true);
    try {
      await updateProfile(token, {
        full_name: data.full_name || null,
        profession: data.profession || null,
        institution: data.institution || null,
      });
      await refreshProfile();
      toast.success(t('saveSuccess'));
      reset(data);
    } catch {
      toast.error(t('saveError'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex-1 flex items-start justify-center py-12">
      <div className="w-full max-w-md">
        <div className="glass p-8 rounded-2xl">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            {t('title')}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-8">{user?.email}</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t('fullName')}
              </label>
              <input
                {...register('full_name')}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple"
                placeholder={t('fullNamePlaceholder')}
              />
              {errors.full_name && (
                <p className="text-xs text-red-500 mt-1">{errors.full_name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t('profession')}
              </label>
              <input
                {...register('profession')}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple"
                placeholder={t('professionPlaceholder')}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                {t('institution')}
              </label>
              <input
                {...register('institution')}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple"
                placeholder={t('institutionPlaceholder')}
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !isDirty}
              className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? t('saving') : t('save')}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <AuthGuard>
      <ProfileForm />
    </AuthGuard>
  );
}
