'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Annotation } from './AnnotatedText';
import { Info, X } from 'lucide-react';
import { createPortal } from 'react-dom';

interface IssueTooltipProps {
  annotation: Annotation;
  children: React.ReactNode;
  onOpenSidePanel: () => void;
  /** Skip the default text-highlight classes — used when the child element provides its own visual (e.g. PDF bbox overlay). */
  noHighlight?: boolean;
}

const severityConfig = {
  outdated: {
    label: 'Outdated',
    bgColor: 'bg-sky-100 dark:bg-sky-900/40',
    textColor: 'text-sky-700 dark:text-sky-300',
    highlightColor: 'bg-sky-200/80 dark:bg-sky-900/60 border-b-2 border-sky-500',
    activeHighlight: 'bg-sky-300 dark:bg-sky-800 border-b-2 border-sky-600 ring-2 ring-sky-400/50',
    dotColor: 'bg-sky-500',
  },
  biased: {
    label: 'Biased',
    bgColor: 'bg-amber-100 dark:bg-amber-900/40',
    textColor: 'text-amber-700 dark:text-amber-300',
    highlightColor: 'bg-amber-200/80 dark:bg-amber-900/60 border-b-2 border-amber-500',
    activeHighlight: 'bg-amber-300 dark:bg-amber-800 border-b-2 border-amber-600 ring-2 ring-amber-400/50',
    dotColor: 'bg-amber-500',
  },
  potentially_offensive: {
    label: 'Potentially Offensive',
    bgColor: 'bg-rose-100 dark:bg-rose-900/40',
    textColor: 'text-rose-700 dark:text-rose-300',
    highlightColor: 'bg-rose-200/80 dark:bg-rose-900/60 border-b-2 border-rose-500',
    activeHighlight: 'bg-rose-300 dark:bg-rose-800 border-b-2 border-rose-600 ring-2 ring-rose-400/50',
    dotColor: 'bg-rose-500',
  },
  factually_incorrect: {
    label: 'Factually Incorrect',
    bgColor: 'bg-red-100 dark:bg-red-900/40',
    textColor: 'text-red-700 dark:text-red-300',
    highlightColor: 'bg-red-200/80 dark:bg-red-900/60 border-b-2 border-red-500',
    activeHighlight: 'bg-red-300 dark:bg-red-800 border-b-2 border-red-600 ring-2 ring-red-400/50',
    dotColor: 'bg-red-500',
  },
};

export default function IssueTooltip({ annotation, children, onOpenSidePanel, noHighlight = false }: IssueTooltipProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isPinned, setIsPinned] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0, arrowX: 144, showBelow: false });
  const [isMounted, setIsMounted] = useState(false);
  const triggerRef = useRef<HTMLSpanElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const config = severityConfig[annotation.severity] || severityConfig.biased;
  const isVisible = isHovered || isPinned;

  // eslint-disable-next-line react-hooks/set-state-in-effect -- Initialization pattern for portal mounting
  useEffect(() => { setIsMounted(true); }, []);

  const updatePosition = useCallback(() => {
    if (!triggerRef.current) return;

    const rect = triggerRef.current.getBoundingClientRect();
    const tooltipWidth = 288;
    const padding = 12;

    // Horizontal: centre on the phrase, clamp to viewport
    let x = rect.left + rect.width / 2 - tooltipWidth / 2;
    if (x < padding) x = padding;
    else if (x + tooltipWidth > window.innerWidth - padding)
      x = window.innerWidth - tooltipWidth - padding;

    const phraseCenter = rect.left + rect.width / 2;
    const arrowX = Math.max(20, Math.min(phraseCenter - x, tooltipWidth - 20));

    // Direction: go above unless there's significantly more room below
    const spaceAbove = rect.top - padding;
    const spaceBelow = window.innerHeight - rect.bottom - padding;
    const showBelow = spaceAbove < 160 || spaceBelow > spaceAbove + 80;

    const y = showBelow ? rect.bottom + padding : rect.top - padding;

    setPosition({ x, y, arrowX, showBelow });

    // After paint, measure the real rendered bounds and nudge if still overflowing.
    // Runs on every position update (hover AND click), not just on first mount.
    requestAnimationFrame(() => {
      if (!tooltipRef.current) return;
      const r = tooltipRef.current.getBoundingClientRect();
      const pad = 8;
      let dy = 0;
      if (r.bottom > window.innerHeight - pad) dy = window.innerHeight - pad - r.bottom;
      else if (r.top < pad) dy = pad - r.top;
      if (dy !== 0) setPosition(p => ({ ...p, y: p.y + dy }));
    });
  }, []);

  useEffect(() => {
    if (!isVisible) return;
    updatePosition();
    const handleScroll = (e: Event) => {
        // Ignore scroll events that come from inside the tooltip (user scrolling the body)
        if (tooltipRef.current?.contains(e.target as Node)) return;
        if (isPinned) setIsPinned(false);
        else setIsHovered(false);
      };
      window.addEventListener('scroll', handleScroll, true);
      return () => window.removeEventListener('scroll', handleScroll, true);
  }, [isVisible, updatePosition, isPinned]);

  useEffect(() => {
    if (!isPinned) return;

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        triggerRef.current &&
        !triggerRef.current.contains(target) &&
        tooltipRef.current &&
        !tooltipRef.current.contains(target)
      ) {
        setIsPinned(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isPinned]);

  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => {
      if (!isPinned) {
        updatePosition();
        setIsHovered(true);
      }
    }, 150);
  };

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    hoverTimeoutRef.current = setTimeout(() => {
      setIsHovered(false);
    }, 100);
  };

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    updatePosition();
    setIsPinned(true);
    setIsHovered(false);
  };

  const handleClose = () => {
    setIsPinned(false);
    setIsHovered(false);
  };

  const handleViewDetails = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsPinned(false);
    setIsHovered(false);
    onOpenSidePanel();
  };

  useEffect(() => {
    return () => {
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    };
  }, []);

  const tooltipContent = (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          ref={tooltipRef}
          initial={{ opacity: 0, y: 8, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8, scale: 0.96 }}
          transition={{ duration: 0.15, ease: 'easeOut' }}
          className="fixed z-[9999]"
          style={{
            left: position.x,
            top: position.y,
            transform: position.showBelow ? 'translateY(0)' : 'translateY(-100%)',
          }}
          onMouseEnter={() => {
            if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
            if (!isPinned) setIsHovered(true);
          }}
          onMouseLeave={handleMouseLeave}
        >
          <div
            className={cn(
              'w-64 rounded-xl shadow-2xl border relative flex flex-col',
              'bg-white dark:bg-slate-900',
              'border-slate-200 dark:border-slate-700',
              isPinned && 'ring-2 ring-pride-purple/30'
            )}
          >
            {/* Severity + category */}
            <div className="flex items-center gap-2 px-4 pt-3 pb-2 shrink-0">
              <span className={cn('w-2 h-2 rounded-full shrink-0', config.dotColor)} />
              <span className={cn(
                'text-xs font-semibold px-2 py-0.5 rounded-full shrink-0',
                config.bgColor,
                config.textColor
              )}>
                {config.label}
              </span>
              {annotation.category && (
                <span className="text-xs text-slate-400 dark:text-slate-500 truncate">
                  {annotation.category}
                </span>
              )}
              {isPinned && (
                <button
                  onClick={handleClose}
                  className="ml-auto p-1 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors shrink-0"
                  aria-label="Close tooltip"
                >
                  <X className="w-3.5 h-3.5 text-slate-400" />
                </button>
              )}
            </div>

            {/* View details button */}
            <div className="px-3 pb-3 shrink-0">
              <button
                onClick={handleViewDetails}
                className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-pride-purple/10 hover:bg-pride-purple/20 text-pride-purple font-medium text-xs transition-colors"
              >
                <Info className="w-3.5 h-3.5" />
                View full details
              </button>
            </div>

            {/* Arrow pointing to the phrase */}
            <div
              className={cn(
                "absolute w-4 h-4 bg-white dark:bg-slate-900",
                position.showBelow
                  ? "-top-2 border-l border-t border-slate-200 dark:border-slate-700"
                  : "-bottom-2 border-r border-b border-slate-200 dark:border-slate-700"
              )}
              style={{
                left: position.arrowX,
                transform: 'translateX(-50%) rotate(45deg)',
              }}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  return (
    <>
      <span
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
        className={noHighlight ? undefined : cn(
          'cursor-pointer rounded-sm px-0.5 transition-all duration-200',
          isPinned ? config.activeHighlight : config.highlightColor,
          'hover:opacity-90'
        )}
        style={noHighlight ? { display: 'block', width: '100%', height: '100%', cursor: 'pointer' } : undefined}
      >
        {children}
      </span>

      {isMounted && createPortal(tooltipContent, document.body)}
    </>
  );
}

export { severityConfig };
