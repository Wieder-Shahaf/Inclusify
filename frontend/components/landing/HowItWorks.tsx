'use client';

import { motion } from 'framer-motion';
import { Upload, Scan, FileCheck } from 'lucide-react';

interface HowItWorksProps {
  isHebrew: boolean;
  translations: {
    title: string;
    subtitle: string;
    step1Title: string;
    step1Desc: string;
    step2Title: string;
    step2Desc: string;
    step3Title: string;
    step3Desc: string;
  };
}

export default function HowItWorks({ isHebrew, translations }: HowItWorksProps) {
  const steps = [
    {
      icon: Upload,
      title: translations.step1Title,
      description: translations.step1Desc,
      color: 'from-pride-purple to-pride-blue',
    },
    {
      icon: Scan,
      title: translations.step2Title,
      description: translations.step2Desc,
      color: 'from-pride-pink to-pride-purple',
    },
    {
      icon: FileCheck,
      title: translations.step3Title,
      description: translations.step3Desc,
      color: 'from-pride-orange to-pride-pink',
    },
  ];

  // Reverse order for RTL
  const displaySteps = isHebrew ? [...steps].reverse() : steps;

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

        <div className="grid md:grid-cols-3 gap-6 relative">
          {/* Connection Line (desktop only) */}
          <div className={`hidden md:block absolute top-16 left-[16.67%] right-[16.67%] h-0.5 bg-gradient-to-r ${isHebrew ? 'from-pride-orange via-pride-pink to-pride-purple' : 'from-pride-purple via-pride-pink to-pride-orange'} opacity-20`} />

          {displaySteps.map((step, idx) => {
            const Icon = step.icon;
            // For RTL, reverse the step numbers
            const stepNumber = isHebrew ? 3 - idx : idx + 1;
            return (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: idx * 0.1 }}
                className="relative"
              >
                <div className="flex flex-col items-center text-center">
                  {/* Step Number & Icon */}
                  <div className="relative mb-4">
                    <motion.div
                      className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${step.color} flex items-center justify-center shadow-lg`}
                      whileHover={{ scale: 1.05, rotate: 5 }}
                      transition={{ type: 'spring', stiffness: 300 }}
                    >
                      <Icon className="w-8 h-8 text-white" />
                    </motion.div>
                    <div className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-white dark:bg-slate-900 border-2 border-pride-purple flex items-center justify-center text-xs font-bold text-pride-purple">
                      {stepNumber}
                    </div>
                  </div>

                  {/* Content */}
                  <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-2">
                    {step.title}
                  </h3>
                  <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
