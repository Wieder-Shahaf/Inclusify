'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { FileText, Search, Sparkles, CheckCircle2, Upload, Loader2 } from 'lucide-react';

interface Translations {
  uploading: string;
  uploadingDesc: string;
  parsing: string;
  parsingDesc: string;
  analyzing: string;
  analyzingDesc: string;
  generating: string;
  generatingDesc: string;
  complete: string;
  completeDesc: string;
}

type ProcessingStage = 'uploading' | 'parsing' | 'analyzing' | 'generating' | 'complete';

interface ProcessingAnimationProps {
  fileName: string;
  onComplete?: () => void;  // Optional - only for demo mode
  translations?: Translations;
  stage?: ProcessingStage;  // External stage control
  showExtendedWait?: boolean;  // For long wait message
  extendedWaitMessage?: string;  // Translation
}

const defaultTranslations: Translations = {
  uploading: 'Uploading document',
  uploadingDesc: 'Securely transferring your file...',
  parsing: 'Parsing content',
  parsingDesc: 'Extracting text from document...',
  analyzing: 'Checking for non-inclusive writing...',
  analyzingDesc: 'Scanning for LGBTQ+ non-inclusive language...',
  generating: 'Generating insights',
  generatingDesc: 'Preparing your personalized report...',
  complete: 'Analysis complete',
  completeDesc: 'Your results are ready!',
};

const TOTAL_DURATION = 6000; // 6 seconds total

const stageToIndex: Record<ProcessingStage, number> = {
  uploading: 0,
  parsing: 1,
  analyzing: 2,
  generating: 3,
  complete: 4,
};

// Pre-compute particle positions at module level to avoid impure function during render
const PARTICLE_POSITIONS = [
  { x: -35, y: -65 },
  { x: 28, y: -72 },
  { x: -18, y: -58 },
  { x: 40, y: -45 },
  { x: -30, y: -80 },
  { x: 15, y: -55 },
  { x: -40, y: -48 },
  { x: 32, y: -68 },
];

export default function ProcessingAnimation({ fileName, onComplete, translations, stage, showExtendedWait, extendedWaitMessage }: ProcessingAnimationProps) {
  const t = { ...defaultTranslations, ...translations };

  const stages = [
    { id: 'uploading', label: t.uploading, description: t.uploadingDesc, icon: Upload },
    { id: 'parsing', label: t.parsing, description: t.parsingDesc, icon: FileText },
    { id: 'analyzing', label: t.analyzing, description: t.analyzingDesc, icon: Search },
    { id: 'generating', label: t.generating, description: t.generatingDesc, icon: Sparkles },
    { id: 'complete', label: t.complete, description: t.completeDesc, icon: CheckCircle2 },
  ];

  // Timer-based state (only used when no external stage prop)
  const [timerProgress, setTimerProgress] = useState(0);
  const [timerStageIndex, setTimerStageIndex] = useState(0);
  const startTimeRef = useRef<number>(0);
  const animationFrameRef = useRef<number>(0);

  // Derive values from external stage prop, or fall back to timer state
  const currentStageIndex = stage !== undefined ? stageToIndex[stage] : timerStageIndex;
  const progress = stage !== undefined
    ? (stage === 'complete' ? 100 : Math.min((stageToIndex[stage] + 1) * 25, 95))
    : timerProgress;
  const currentStage = stages[currentStageIndex];

  useEffect(() => {
    // External stage is controlled by parent — no timer needed
    if (stage !== undefined) return;

    startTimeRef.current = Date.now();

    const animate = () => {
      const elapsed = Date.now() - startTimeRef.current;
      const newProgress = Math.min((elapsed / TOTAL_DURATION) * 100, 100);

      setTimerProgress(Math.round(newProgress));

      if (newProgress < 20) {
        setTimerStageIndex(0);
      } else if (newProgress < 40) {
        setTimerStageIndex(1);
      } else if (newProgress < 70) {
        setTimerStageIndex(2);
      } else if (newProgress < 95) {
        setTimerStageIndex(3);
      } else {
        setTimerStageIndex(4);
      }

      if (newProgress < 100) {
        animationFrameRef.current = requestAnimationFrame(animate);
      } else {
        if (onComplete) {
          setTimeout(onComplete, 500);
        }
      }
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [stage, onComplete]);

  return (
    <div className="w-full max-w-lg mx-auto">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="p-8 rounded-2xl glass border"
      >
        {/* Document Animation */}
        <div className="flex justify-center mb-8">
          <motion.div
            className="relative"
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          >
            {/* Glow Effect */}
            <motion.div
              className="absolute inset-0 blur-2xl bg-gradient-to-br from-pride-purple/40 to-pride-pink/40 rounded-full scale-150"
              animate={{ opacity: [0.4, 0.7, 0.4] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
            />

            {/* Document Icon Container */}
            <motion.div
              className="relative w-24 h-28 rounded-xl bg-gradient-to-br from-pride-purple to-pride-pink p-1"
              animate={{
                boxShadow: [
                  '0 0 20px rgba(123,97,255,0.3)',
                  '0 0 40px rgba(123,97,255,0.5)',
                  '0 0 20px rgba(123,97,255,0.3)',
                ],
              }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
            >
              <div className="w-full h-full bg-white dark:bg-slate-900 rounded-lg flex flex-col items-center justify-center overflow-hidden relative">
                <FileText className="w-10 h-10 text-pride-purple" />

                {/* Scanning Line */}
                <motion.div
                  className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-pride-purple to-transparent"
                  animate={{ top: ['0%', '100%'] }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                />
              </div>
            </motion.div>

            {/* Floating Particles */}
            {PARTICLE_POSITIONS.map((particle, i) => (
              <motion.div
                key={i}
                className="absolute w-2 h-2 rounded-full"
                style={{
                  background: i % 2 === 0 ? '#7b61ff' : '#ff53a1',
                  left: '50%',
                  top: '50%',
                }}
                animate={{
                  x: [0, particle.x],
                  y: [0, particle.y],
                  scale: [0, 1, 0],
                  opacity: [0, 0.8, 0],
                }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  delay: i * 0.2,
                  ease: 'easeOut',
                }}
              />
            ))}
          </motion.div>
        </div>

        {/* File Name */}
        <div className="text-center mb-6">
          <p className="text-sm text-slate-500 dark:text-slate-400 truncate max-w-xs mx-auto px-4">
            {fileName}
          </p>
        </div>

        {/* Progress Bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-slate-600 dark:text-slate-300 font-medium">
              {currentStage.label}
            </span>
            <span className="text-pride-purple font-bold tabular-nums">{progress}%</span>
          </div>
          <div className="h-3 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-pride-purple via-pride-pink to-pride-purple rounded-full relative"
              style={{ width: `${progress}%` }}
              transition={{ duration: 0.1 }}
            >
              {/* Shimmer effect */}
              <motion.div
                className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                animate={{ x: ['-100%', '200%'] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
              />
            </motion.div>
          </div>
        </div>

        {/* Stage Description */}
        <AnimatePresence mode="wait">
          <motion.p
            key={currentStage.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="text-center text-sm text-slate-500 dark:text-slate-400"
          >
            {currentStage.description}
          </motion.p>
        </AnimatePresence>

        {/* Extended Wait Message */}
        {showExtendedWait && extendedWaitMessage && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center text-xs text-amber-600 dark:text-amber-400 mt-2"
          >
            {extendedWaitMessage}
          </motion.p>
        )}

        {/* Stage Indicators */}
        <div className="flex justify-center items-center gap-2 mt-8">
          {stages.slice(0, -1).map((stage, index) => {
            const isActive = index === currentStageIndex;
            const isCompleted = index < currentStageIndex;
            const Icon = stage.icon;

            return (
              <motion.div
                key={stage.id}
                className={cn(
                  'flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300',
                  isCompleted && 'bg-pride-purple text-white',
                  isActive && 'bg-pride-purple/20 text-pride-purple ring-2 ring-pride-purple',
                  !isActive && !isCompleted && 'bg-slate-100 dark:bg-slate-800 text-slate-400'
                )}
                animate={isActive ? { scale: [1, 1.1, 1] } : {}}
                transition={{ duration: 0.6, repeat: isActive ? Infinity : 0 }}
              >
                {isCompleted ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : isActive ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Icon className="w-5 h-5" />
                )}
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </div>
  );
}
