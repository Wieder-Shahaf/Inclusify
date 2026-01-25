'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { ArrowRight, Sparkles } from 'lucide-react';

interface HeroSectionProps {
  locale: string;
  isHebrew: boolean;
  translations: {
    headline: string;
    headlineTop: string;
    headlineBottom: string;
    subheadline: string;
    cta: string;
    secondaryCta: string;
    badge: string;
    trustFree: string;
    trustNoSignup: string;
    trustPrivacy: string;
  };
}

export default function HeroSection({ locale, isHebrew, translations }: HeroSectionProps) {
  return (
    <section className="relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 -z-10">
        {/* Gradient Orbs */}
        <motion.div
          className="absolute top-0 right-0 w-[600px] h-[600px] rounded-full opacity-30 blur-3xl"
          style={{
            background: 'radial-gradient(circle, rgba(123,97,255,0.4) 0%, transparent 70%)',
          }}
          animate={{
            scale: [1, 1.2, 1],
            x: [0, 30, 0],
            y: [0, -20, 0],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        <motion.div
          className="absolute bottom-0 left-0 w-[500px] h-[500px] rounded-full opacity-25 blur-3xl"
          style={{
            background: 'radial-gradient(circle, rgba(255,83,161,0.4) 0%, transparent 70%)',
          }}
          animate={{
            scale: [1, 1.15, 1],
            x: [0, -20, 0],
            y: [0, 30, 0],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />

        {/* Grid Pattern */}
        <div
          className="absolute inset-0 opacity-[0.02] dark:opacity-[0.05]"
          style={{
            backgroundImage: `linear-gradient(rgba(123,97,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(123,97,255,0.5) 1px, transparent 1px)`,
            backgroundSize: '60px 60px',
          }}
        />
      </div>

      <div className="max-w-5xl mx-auto text-center pt-8 pb-12 px-4">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-pride-purple/10 border border-pride-purple/20 mb-6"
        >
          <Sparkles className="w-4 h-4 text-pride-purple" />
          <span className="text-sm font-medium text-pride-purple">{translations.badge}</span>
        </motion.div>

        {/* Main Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className={`text-4xl sm:text-5xl md:text-6xl lg:text-7xl ${
            isHebrew ? 'font-light hebrew-hero' : 'font-black'
          } tracking-tight leading-[1.1] mb-6`}
        >
          <span className="block text-slate-800 dark:text-white">{translations.headlineTop}</span>
          <span className="block bg-gradient-to-r from-pride-purple via-pride-pink to-pride-purple bg-clip-text text-transparent bg-[length:200%_auto] animate-gradient">
            {translations.headlineBottom}
          </span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-lg sm:text-xl text-slate-600 dark:text-slate-300 max-w-2xl mx-auto mb-8 leading-relaxed"
        >
          {translations.subheadline}
        </motion.p>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Link
            href={`/${locale}/analyze`}
            className="group relative inline-flex items-center justify-center gap-2 rounded-xl px-8 py-4 font-semibold text-white bg-gradient-to-r from-pride-purple to-pride-pink shadow-lg shadow-pride-purple/25 hover:shadow-xl hover:shadow-pride-purple/30 transition-all duration-300 hover:scale-105"
          >
            {translations.cta}
            <ArrowRight className={`w-5 h-5 transition-transform ${isHebrew ? 'rotate-180 group-hover:-translate-x-1' : 'group-hover:translate-x-1'}`} />
          </Link>
          <Link
            href={`/${locale}/glossary`}
            className="inline-flex items-center justify-center gap-2 rounded-xl px-8 py-4 font-semibold text-slate-700 dark:text-slate-200 bg-white/50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 hover:bg-white dark:hover:bg-slate-800 transition-all duration-300"
          >
            {translations.secondaryCta}
          </Link>
        </motion.div>

        {/* Trust Indicators */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="mt-10 flex items-center justify-center gap-6 text-sm text-slate-500 dark:text-slate-400"
        >
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span>{translations.trustFree}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-pride-purple" />
            <span>{translations.trustNoSignup}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-pride-pink" />
            <span>{translations.trustPrivacy}</span>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
