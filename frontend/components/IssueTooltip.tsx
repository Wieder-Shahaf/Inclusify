'use client';

import { useState, useRef, useEffect, useCallback, useId } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Annotation } from './AnnotatedText';
import { Info, X } from 'lucide-react';
import { createPortal } from 'react-dom';

const ACTIVE_TOOLTIP_EVENT = 'inclusify:issue-tooltip-active';

type ActiveTooltipEventDetail = {
  id: string;
};

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
    bgColor: 'bg-orange-100 dark:bg-orange-900/40',
    textColor: 'text-orange-700 dark:text-orange-300',
    highlightColor: 'bg-orange-200/80 dark:bg-orange-900/60 border-b-2 border-orange-500',
    activeHighlight: 'bg-orange-300 dark:bg-orange-800 border-b-2 border-orange-600 ring-2 ring-orange-400/50',
    dotColor: 'bg-orange-500',
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
  const tooltipId = useId();
  const triggerRef = useRef<HTMLSpanElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const config = severityConfig[annotation.severity] || severityConfig.biased;
  const isVisible = isHovered || isPinned;

  const updatePosition = useCallback(() => {
    if (!triggerRef.current) return;

    const rect = triggerRef.current.getBoundingClientRect();
    const tooltipWidth = tooltipRef.current?.offsetWidth ?? 288;
    const tooltipHeight = tooltipRef.current?.offsetHeight ?? 180;
    const padding = 12;

    // Always anchor to the trigger's current viewport rect for scroll-safe positioning.
    const anchorX = rect.left + rect.width / 2;

    // Horizontal: center tooltip on phrase center and clamp to viewport.
    let x = anchorX - tooltipWidth / 2;
    if (x < padding) x = padding;
    else if (x + tooltipWidth > window.innerWidth - padding)
      x = window.innerWidth - tooltipWidth - padding;

    const arrowX = Math.max(20, Math.min(anchorX - x, tooltipWidth - 20));

    const spaceAbove = rect.top - padding;
    const spaceBelow = window.innerHeight - rect.bottom - padding;
    const showBelow = spaceAbove < 160 || spaceBelow > spaceAbove + 80;

    let y = showBelow ? rect.bottom + padding : rect.top - tooltipHeight - padding;
    if (y < padding) y = padding;
    if (y + tooltipHeight > window.innerHeight - padding) y = Math.max(padding, window.innerHeight - tooltipHeight - padding);

    setPosition({ x, y, arrowX, showBelow });
  }, []);

  useEffect(() => {
    if (!isVisible) return;
    updatePosition();

    const onLayoutChange = () => updatePosition();
    window.addEventListener('scroll', onLayoutChange, true);
    window.addEventListener('resize', onLayoutChange);

    const triggerObserver = triggerRef.current ? new ResizeObserver(onLayoutChange) : null;
    const tooltipObserver = tooltipRef.current ? new ResizeObserver(onLayoutChange) : null;
    if (triggerRef.current && triggerObserver) triggerObserver.observe(triggerRef.current);
    if (tooltipRef.current && tooltipObserver) tooltipObserver.observe(tooltipRef.current);

    return () => {
      window.removeEventListener('scroll', onLayoutChange, true);
      window.removeEventListener('resize', onLayoutChange);
      triggerObserver?.disconnect();
      tooltipObserver?.disconnect();
    };
  }, [isVisible, updatePosition]);

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

  useEffect(() => {
    const handleTooltipActivated = (event: Event) => {
      const customEvent = event as CustomEvent<ActiveTooltipEventDetail>;
      if (customEvent.detail?.id === tooltipId) return;
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
      setIsHovered(false);
      setIsPinned(false);
    };

    window.addEventListener(ACTIVE_TOOLTIP_EVENT, handleTooltipActivated as EventListener);
    return () => {
      window.removeEventListener(ACTIVE_TOOLTIP_EVENT, handleTooltipActivated as EventListener);
    };
  }, [tooltipId]);

  const markAsActiveTooltip = () => {
    window.dispatchEvent(
      new CustomEvent<ActiveTooltipEventDetail>(ACTIVE_TOOLTIP_EVENT, {
        detail: { id: tooltipId },
      }),
    );
  };

  const handleMouseEnter = () => {
    if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
    markAsActiveTooltip();
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
    markAsActiveTooltip();
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
            {/* Severity + confidence + close */}
            <div className="px-4 pt-3 pb-2 shrink-0">
              <div className="flex items-center gap-2">
                <span className={cn('w-2 h-2 rounded-full shrink-0', config.dotColor)} />
                <span className={cn(
                  'text-xs font-semibold px-2 py-0.5 rounded-full shrink-0',
                  config.bgColor,
                  config.textColor
                )}>
                  {config.label}
                </span>
                <div className="ml-auto flex items-center gap-1.5 shrink-0">
                  {annotation.confidence != null && (
                    <span className="text-xs text-slate-400 dark:text-slate-500 tabular-nums">
                      {Math.round(annotation.confidence * 100)}%
                    </span>
                  )}
                  {isPinned && (
                    <button
                      onClick={handleClose}
                      className="p-1 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                      aria-label="Close tooltip"
                    >
                      <X className="w-3.5 h-3.5 text-slate-400" />
                    </button>
                  )}
                </div>
              </div>
              {annotation.category && (
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 pl-4 leading-snug">
                  {annotation.category}
                </p>
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

      {typeof document !== 'undefined' && createPortal(tooltipContent, document.body)}
    </>
  );
}

export { severityConfig };
