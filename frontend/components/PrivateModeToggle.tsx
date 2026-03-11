'use client';

import { useTranslations } from 'next-intl';
import { Lock } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface PrivateModeToggleProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  disabled?: boolean;
}

export default function PrivateModeToggle({
  checked,
  onCheckedChange,
  disabled = false,
}: PrivateModeToggleProps) {
  const t = useTranslations('analyzer');

  return (
    <TooltipProvider delayDuration={300}>
      <div className="flex items-center gap-3">
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4 text-slate-500 dark:text-slate-400" />
              <label
                htmlFor="private-mode-toggle"
                className="text-sm font-medium text-slate-700 dark:text-slate-200 cursor-pointer"
              >
                {t('privateMode.label')}
              </label>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>{t('privateMode.tooltip')}</p>
          </TooltipContent>
        </Tooltip>
        <Switch
          id="private-mode-toggle"
          checked={checked}
          onCheckedChange={onCheckedChange}
          disabled={disabled}
          aria-label={t('privateMode.label')}
        />
      </div>
    </TooltipProvider>
  );
}
