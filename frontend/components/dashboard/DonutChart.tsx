'use client';

import { useMemo } from 'react';

export type DonutDatum = {
  label: string;
  value: number;
  color: string;
};

export default function DonutChart({
  data,
  size = 260,
  thickness = 22,
  center,
}: {
  data: DonutDatum[];
  size?: number;
  thickness?: number;
  center?: {
    title?: string;
    subtitle?: string;
    titleClassName?: string;
    subtitleClassName?: string;
  };
}) {
  const total = data.reduce((s, d) => s + d.value, 0);
  const radius = (size - thickness) / 2;
  const circumference = 2 * Math.PI * radius;

  // Precompute segment data with offsets using reduce to avoid mutation
  const segments = useMemo(() => {
    const result: Array<{
      label: string;
      value: number;
      color: string;
      len: number;
      dashArray: string;
      dashOffset: number;
    }> = [];

    data.reduce((offset, d) => {
      const frac = d.value / total;
      const len = circumference * frac;
      result.push({
        ...d,
        len,
        dashArray: `${len} ${circumference - len}`,
        dashOffset: -offset,
      });
      return offset + len;
    }, 0);

    return result;
  }, [data, total, circumference]);

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="block">
        <g transform={`translate(${size / 2}, ${size / 2})`}>
          <circle
            r={radius}
            fill="none"
            stroke="currentColor"
            opacity="0.08"
            strokeWidth={thickness}
          />
          {segments.map((segment, i) => (
            <circle
              key={i}
              r={radius}
              fill="none"
              stroke={segment.color}
              strokeWidth={thickness}
              strokeDasharray={segment.dashArray}
              strokeDashoffset={segment.dashOffset}
              transform="rotate(-90)"
              strokeLinecap="round"
            />
          ))}
        </g>
      </svg>
      {center && (
        <div className="absolute inset-0 grid place-items-center text-center">
          <div>
            {center.title && (
              <div className={center.titleClassName ?? 'text-xl font-extrabold'}>
                {center.title}
              </div>
            )}
            {center.subtitle && (
              <div
                className={
                  center.subtitleClassName ?? 'text-xs text-slate-500 dark:text-slate-400'
                }
              >
                {center.subtitle}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
