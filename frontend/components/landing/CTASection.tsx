'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { ArrowRight, FileText, Shield, Zap } from 'lucide-react';

interface CTASectionProps {
  locale: string;
  translations: {
    title: string;
    subtitle: string;
    formats: string;
    instant: string;
    private: string;
    cta: string;
  };
}

export default function CTASection({ locale, translations }: CTASectionProps) {
  const isHebrew = locale === 'he';

  return (
    <section className="py-12 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="max-w-4xl mx-auto"
      >
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-pride-purple via-pride-pink to-pride-purple p-8 sm:p-12 text-center">
          {/* Background Pattern */}
          <div className="absolute inset-0 opacity-10">
            <div
              className="absolute inset-0"
              style={{
                backgroundImage: `radial-gradient(circle at 25% 25%, white 1px, transparent 1px), radial-gradient(circle at 75% 75%, white 1px, transparent 1px)`,
                backgroundSize: '40px 40px',
              }}
            />
          </div>

          {/* Glowing Orbs */}
          <div className="absolute top-0 left-1/4 w-64 h-64 bg-white/20 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-white/10 rounded-full blur-3xl" />

          <div className="relative z-10">
            <motion.h2
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
              className="text-2xl sm:text-3xl md:text-4xl font-bold text-white mb-4"
            >
              {translations.title}
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
              className="text-white/80 text-lg mb-8 max-w-xl mx-auto"
            >
              {translations.subtitle}
            </motion.p>

            {/* Features Row */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.3 }}
              className="flex flex-wrap items-center justify-center gap-6 mb-8 text-white/90 text-sm"
            >
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                <span>{translations.formats}</span>
              </div>
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4" />
                <span>{translations.instant}</span>
              </div>
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4" />
                <span>{translations.private}</span>
              </div>
            </motion.div>

            {/* CTA Button */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.4 }}
            >
              <Link
                href={`/${locale}/analyze`}
                className="group inline-flex items-center justify-center gap-2 rounded-xl px-8 py-4 font-semibold text-pride-purple bg-white shadow-xl hover:shadow-2xl transition-all duration-300 hover:scale-105"
              >
                {translations.cta}
                <ArrowRight className={`w-5 h-5 transition-transform ${isHebrew ? 'rotate-180 group-hover:-translate-x-1' : 'group-hover:translate-x-1'}`} />
              </Link>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
