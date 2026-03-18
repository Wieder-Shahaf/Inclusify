'use client';

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, BookOpen, Heart, Users, Sparkles, ExternalLink, ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface GlossaryTerm {
  term: string;
  definition: string;
  category: 'identity' | 'orientation' | 'expression' | 'concepts';
  note?: string;
  related?: string[];
}

interface GlossaryClientProps {
  terms: GlossaryTerm[];
  translations: {
    title: string;
    subtitle: string;
    searchPlaceholder: string;
    badge: string;
    categories: {
      all: string;
      identity: string;
      orientation: string;
      expression: string;
      concepts: string;
    };
    sourcesTitle: string;
    sourcesDesc: string;
    noResults: string;
    relatedTerms: string;
  };
  isHebrew?: boolean;
}

const categoryConfig = {
  identity: {
    icon: Users,
    color: 'from-purple-500 to-indigo-500',
    bgColor: 'bg-purple-50 dark:bg-purple-950/30',
    borderColor: 'border-purple-200 dark:border-purple-800/50',
    textColor: 'text-purple-700 dark:text-purple-300',
  },
  orientation: {
    icon: Heart,
    color: 'from-pink-500 to-rose-500',
    bgColor: 'bg-pink-50 dark:bg-pink-950/30',
    borderColor: 'border-pink-200 dark:border-pink-800/50',
    textColor: 'text-pink-700 dark:text-pink-300',
  },
  expression: {
    icon: Sparkles,
    color: 'from-amber-500 to-orange-500',
    bgColor: 'bg-amber-50 dark:bg-amber-950/30',
    borderColor: 'border-amber-200 dark:border-amber-800/50',
    textColor: 'text-amber-700 dark:text-amber-300',
  },
  concepts: {
    icon: BookOpen,
    color: 'from-teal-500 to-cyan-500',
    bgColor: 'bg-teal-50 dark:bg-teal-950/30',
    borderColor: 'border-teal-200 dark:border-teal-800/50',
    textColor: 'text-teal-700 dark:text-teal-300',
  },
};

const sources = [
  { name: 'Human Rights Campaign', url: 'https://www.hrc.org/resources/glossary-of-terms' },
  { name: 'PFLAG', url: 'https://pflag.org/glossary' },
  { name: 'The Trevor Project', url: 'https://www.thetrevorproject.org/resources/' },
  { name: 'GLAAD', url: 'https://www.glaad.org/reference' },
];

export default function GlossaryClient({ terms, translations, isHebrew = false }: GlossaryClientProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [expandedTerm, setExpandedTerm] = useState<string | null>(null);

  const filteredTerms = useMemo(() => {
    return terms.filter((term) => {
      const matchesSearch =
        searchQuery === '' ||
        term.term.toLowerCase().includes(searchQuery.toLowerCase()) ||
        term.definition.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = selectedCategory === 'all' || term.category === selectedCategory;
      return matchesSearch && matchesCategory;
    });
  }, [terms, searchQuery, selectedCategory]);

  const categories = [
    { key: 'all', label: translations.categories.all },
    { key: 'identity', label: translations.categories.identity },
    { key: 'orientation', label: translations.categories.orientation },
    { key: 'expression', label: translations.categories.expression },
    { key: 'concepts', label: translations.categories.concepts },
  ];

  return (
    <div className="py-8 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-pride-purple/10 border border-pride-purple/20 mb-4">
            <BookOpen className="w-4 h-4 text-pride-purple" />
            <span className="text-sm font-medium text-pride-purple">{translations.badge}</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-800 dark:text-white mb-3">
            {translations.title}
          </h1>
          <p className="text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
            {translations.subtitle}
          </p>
        </motion.div>

        {/* Search and Filter */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8 space-y-4"
        >
          {/* Search */}
          <div className="relative max-w-md mx-auto">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" aria-hidden="true" />
            <input
              type="text"
              aria-label={translations.searchPlaceholder}
              placeholder={translations.searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-12 pr-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-pride-purple/40 transition-all"
            />
          </div>

          {/* Category Filter */}
          <div className="flex flex-wrap justify-center gap-2" role="group" aria-label="Filter by category">
            {categories.map((cat) => (
              <button
                key={cat.key}
                onClick={() => setSelectedCategory(cat.key)}
                aria-pressed={selectedCategory === cat.key}
                className={cn(
                  'px-4 py-2 rounded-lg text-sm font-medium transition-all focus-visible:ring-2 focus-visible:ring-pride-purple focus-visible:ring-offset-2',
                  selectedCategory === cat.key
                    ? 'bg-pride-purple text-white shadow-md'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Terms Grid */}
        <div className="grid gap-4 sm:grid-cols-2">
          <AnimatePresence mode="popLayout">
            {filteredTerms.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="col-span-full text-center py-12"
              >
                <div className="text-4xl mb-4">🔍</div>
                <p className="text-slate-500 dark:text-slate-400">{translations.noResults}</p>
              </motion.div>
            ) : (
              filteredTerms.map((term, idx) => {
                const config = categoryConfig[term.category];
                const Icon = config.icon;
                const isExpanded = expandedTerm === term.term;

                return (
                  <motion.div
                    key={term.term}
                    layout
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ delay: idx * 0.03 }}
                    className={cn(
                      'rounded-2xl border p-5 transition-all cursor-pointer',
                      config.bgColor,
                      config.borderColor,
                      isExpanded && 'ring-2 ring-pride-purple/30'
                    )}
                    onClick={() => setExpandedTerm(isExpanded ? null : term.term)}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={cn(
                          'flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center',
                          config.color
                        )}
                      >
                        <Icon className="w-5 h-5 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <h3 className="font-semibold text-slate-800 dark:text-white">
                            {term.term}
                          </h3>
                          <ChevronDown
                            className={cn(
                              'w-4 h-4 text-slate-400 transition-transform',
                              isExpanded && 'rotate-180'
                            )}
                          />
                        </div>
                        <p
                          className={cn(
                            'text-sm text-slate-600 dark:text-slate-300 mt-1 leading-relaxed',
                            !isExpanded && 'line-clamp-2'
                          )}
                        >
                          {term.definition}
                        </p>

                        <AnimatePresence>
                          {isExpanded && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              exit={{ opacity: 0, height: 0 }}
                              transition={{ duration: 0.2 }}
                            >
                              {term.note && (
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-3 italic border-l-2 border-pride-purple/30 pl-3">
                                  {term.note}
                                </p>
                              )}
                              {term.related && term.related.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-slate-200/50 dark:border-slate-700/50">
                                  <span className="text-xs text-slate-500 dark:text-slate-400">
                                    {translations.relatedTerms}:{' '}
                                  </span>
                                  <span className="text-xs font-medium text-pride-purple">
                                    {term.related.join(', ')}
                                  </span>
                                </div>
                              )}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    </div>
                  </motion.div>
                );
              })
            )}
          </AnimatePresence>
        </div>

        {/* Sources Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-12 p-6 rounded-2xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800"
        >
          <h3 className="font-semibold text-slate-800 dark:text-white mb-4 flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-pride-purple" />
            {translations.sourcesTitle}
          </h3>
          <div className="grid sm:grid-cols-2 gap-3">
            {sources.map((source) => (
              <a
                key={source.name}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-3 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-pride-purple/50 transition-colors group"
              >
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300 group-hover:text-pride-purple transition-colors">
                  {source.name}
                </span>
                <ExternalLink className="w-4 h-4 text-slate-400 group-hover:text-pride-purple transition-colors ml-auto" />
              </a>
            ))}
          </div>
          <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
            {translations.sourcesDesc}
          </p>
        </motion.div>
      </div>
    </div>
  );
}
