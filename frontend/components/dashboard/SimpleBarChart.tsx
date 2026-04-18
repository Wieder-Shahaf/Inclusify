'use client';
import { useMemo } from 'react';

interface SimpleBarChartProps {
  data: number[];
  labels: string[];
  color?: string;
  height?: number;
}

export default function SimpleBarChart({
  data,
  labels,
  color = '#7b61ff',
  height = 200,
}: SimpleBarChartProps) {
  const { bars } = useMemo(() => {
    if (data.length === 0) return { bars: [] };
    const maxVal = Math.max(...data) || 1;
    const width = 800;
    const slot = width / data.length;
    const barWidth = slot * 0.6;
    const gap = slot * 0.4;
    const bars = data.map((v, i) => {
      const barHeight = (v / maxVal) * (height - 40);
      return {
        x: i * slot + gap / 2,
        y: height - 24 - barHeight,
        barHeight,
        barWidth,
        value: v,
      };
    });
    return { bars };
  }, [data, height]);

  return (
    <div className="w-full overflow-hidden">
      <svg
        viewBox={`0 0 800 ${height}`}
        className="w-full h-auto"
        role="img"
        aria-label="Category frequency bar chart"
      >
        {bars.map((b, i) => {
          const rawLabel = labels[i] || '';
          const labelText = rawLabel.length > 14 ? rawLabel.slice(0, 14) + '…' : rawLabel;
          return (
            <g key={i}>
              <rect
                x={b.x}
                y={b.y}
                width={b.barWidth}
                height={b.barHeight}
                fill={color}
                rx="4"
                opacity="0.85"
              />
              <text
                x={b.x + b.barWidth / 2}
                y={b.y - 4}
                textAnchor="middle"
                fontSize="11"
                className="fill-slate-800 dark:fill-white font-bold"
              >
                {b.value}
              </text>
              <text
                x={b.x + b.barWidth / 2}
                y={height - 6}
                textAnchor="middle"
                fontSize="11"
                className="fill-slate-500 dark:fill-slate-400"
              >
                {labelText}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
