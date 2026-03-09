'use client';

import { AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';

interface HealthWarningBannerProps {
  message: string;
}

export default function HealthWarningBanner({ message }: HealthWarningBannerProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 px-4 py-2"
    >
      <div className="max-w-4xl mx-auto flex items-center gap-2 text-amber-700 dark:text-amber-400 text-sm">
        <AlertTriangle className="w-4 h-4 flex-shrink-0" />
        <span>{message}</span>
      </div>
    </motion.div>
  );
}
