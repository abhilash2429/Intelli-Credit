'use client';

import { formatRatio } from '@/lib/formatters';

interface RiskGaugeProps {
  score: number;
  decision: string;
  category: string;
}

function getGaugeColor(score: number) {
  if (score >= 80) return '#22c55e';
  if (score >= 65) return '#84cc16';
  if (score >= 50) return '#eab308';
  if (score >= 35) return '#f97316';
  return '#ef4444';
}

function hexToRgba(hex: string, alpha: number) {
  const cleaned = hex.replace('#', '');
  const value = cleaned.length === 3
    ? cleaned.split('').map((c) => c + c).join('')
    : cleaned;
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export default function RiskGauge({ score, decision, category }: RiskGaugeProps) {
  const clampedScore = Math.min(100, Math.max(0, score));
  const angle = -180 + (clampedScore / 100) * 180;
  const gaugeColor = getGaugeColor(clampedScore);

  const needleX = 150 + 100 * Math.cos((angle * Math.PI) / 180);
  const needleY = 150 + 100 * Math.sin((angle * Math.PI) / 180);

  const getDecisionStyle = (d: string) => {
    const style = {
      backgroundColor: hexToRgba(gaugeColor, 0.12),
      borderColor: hexToRgba(gaugeColor, 0.45),
      color: gaugeColor,
    };
    if (d === 'APPROVE') return style;
    if (d === 'CONDITIONAL_APPROVE') return style;
    if (d === 'REJECT' || d === 'HARD_REJECT') return style;
    return style;
  };

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 300 180" className="w-72">
        {/* Track arc */}
        <path
          d="M 30 150 A 120 120 0 0 1 270 150"
          stroke="var(--ob-surface2)"
          strokeWidth="20"
          fill="none"
          strokeLinecap="round"
        />
        {/* Filled arc — calculated based on score */}
        <path
          d="M 30 150 A 120 120 0 0 1 270 150"
          stroke={gaugeColor}
          strokeWidth="20"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={`${(clampedScore / 100) * 377} 377`}
        />

        {/* Needle */}
        <line
          x1="150"
          y1="150"
          x2={needleX}
          y2={needleY}
          stroke={gaugeColor}
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <circle cx="150" cy="150" r="5" fill={gaugeColor} />

        {/* Score text */}
        <text
          x="150"
          y="138"
          textAnchor="middle"
          fill={gaugeColor}
          fontSize="32"
          fontFamily="DM Serif Display, serif"
        >
          {formatRatio(clampedScore, 1, '')}
        </text>
        <text
          x="150"
          y="163"
          textAnchor="middle"
          fill="var(--ob-muted)"
          fontSize="12"
          fontFamily="Manrope, sans-serif"
        >
          {category}
        </text>
      </svg>

      {/* Decision badge */}
      <div
        className="mt-2 px-4 py-1.5 rounded border text-[11px] uppercase tracking-wider font-medium"
        style={getDecisionStyle(decision)}
      >
        {decision.replace('_', ' ')}
      </div>
    </div>
  );
}
