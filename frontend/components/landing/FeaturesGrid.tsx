'use client';

import { motion } from 'framer-motion';
import {
  Brain,
  Globe,
  AlertTriangle,
  FileDown,
  BookOpen,
  ShieldCheck,
} from 'lucide-react';

interface Feature {
  key: string;
  title: string;
  description: string;
}

interface FeaturesGridProps {
  features: Feature[];
  translations: {
    title: string;
    subtitle: string;
  };
}

const featureIcons: Record<string, typeof Brain> = {
  smartDetection: Brain,
  bilingualSupport: Globe,
  gradedAlerts: AlertTriangle,
  exportableReports: FileDown,
  educationalResources: BookOpen,
  privacyFirst: ShieldCheck,
};

const featureColors: Record<string, string> = {
  smartDetection: 'from-purple-500 to-indigo-500',
  bilingualSupport: 'from-blue-500 to-cyan-500',
  gradedAlerts: 'from-amber-500 to-orange-500',
  exportableReports: 'from-green-500 to-emerald-500',
  educationalResources: 'from-rose-500 to-pink-500',
  privacyFirst: 'from-violet-500 to-purple-500',
};

const featureBgColors: Record<string, string> = {
  smartDetection: 'bg-purple-50 dark:bg-purple-950/30 border-purple-100 dark:border-purple-900/50',
  bilingualSupport: 'bg-blue-50 dark:bg-blue-950/30 border-blue-100 dark:border-blue-900/50',
  gradedAlerts: 'bg-amber-50 dark:bg-amber-950/30 border-amber-100 dark:border-amber-900/50',
  exportableReports: 'bg-green-50 dark:bg-green-950/30 border-green-100 dark:border-green-900/50',
  educationalResources: 'bg-rose-50 dark:bg-rose-950/30 border-rose-100 dark:border-rose-900/50',
  privacyFirst: 'bg-violet-50 dark:bg-violet-950/30 border-violet-100 dark:border-violet-900/50',
};

export default function FeaturesGrid({ features, translations }: FeaturesGridProps) {
  return (
    <section className="py-12 px-4">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-10"
        >
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-800 dark:text-white mb-3">
            {translations.title}
          </h2>
          <p className="text-slate-600 dark:text-slate-400 max-w-xl mx-auto">
            {translations.subtitle}
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map((feature, idx) => {
            const Icon = featureIcons[feature.key] || Brain;
            const iconGradient = featureColors[feature.key] || 'from-pride-purple to-pride-pink';
            const bgColor = featureBgColors[feature.key] || 'bg-slate-50 dark:bg-slate-800/50';

            return (
              <motion.div
                key={feature.key}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: idx * 0.05 }}
                whileHover={{ y: -4, transition: { duration: 0.2 } }}
                className={`group relative rounded-2xl p-5 border ${bgColor} transition-shadow hover:shadow-lg`}
              >
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div
                    className={`flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br ${iconGradient} flex items-center justify-center shadow-md group-hover:scale-110 transition-transform duration-300`}
                  >
                    <Icon className="w-6 h-6 text-white" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-slate-800 dark:text-white mb-1">
                      {feature.title}
                    </h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
