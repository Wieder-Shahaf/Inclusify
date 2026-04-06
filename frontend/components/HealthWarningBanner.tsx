'use client';

import { AlertTriangle, Info } from 'lucide-react';
import { motion } from 'framer-motion';

interface HealthWarningBannerProps {
  message: string;
  variant?: 'error' | 'info';
}

export default function HealthWarningBanner({ message, variant = 'error' }: HealthWarningBannerProps) {
  const isInfo = variant === 'info';
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={
        isInfo
          ? 'bg-sky-50 dark:bg-sky-900/20 border-b border-sky-200 dark:border-sky-800 px-4 py-2'
          : 'bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 px-4 py-2'
      }
    >
      <div className={`max-w-4xl mx-auto flex items-center gap-2 text-sm ${isInfo ? 'text-sky-700 dark:text-sky-400' : 'text-amber-700 dark:text-amber-400'}`}>
        {isInfo
          ? <Info className="w-4 h-4 flex-shrink-0" />
          : <AlertTriangle className="w-4 h-4 flex-shrink-0" />
        }
        <span>{message}</span>
      </div>
    </motion.div>
  );
}
