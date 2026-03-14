'use client';

import { formatRatio } from '@/lib/formatters';

interface RiskGaugeProps {
  score: number;
  decision: string;
  category: string;
}

export default function RiskGauge({ score, decision, category }: RiskGaugeProps) {
  const clampedScore = Math.min(100, Math.max(0, score));
  const angle = -90 + (clampedScore / 100) * 180;

  const needleX = 150 + 100 * Math.cos((angle * Math.PI) / 180);
  const needleY = 150 + 100 * Math.sin((angle * Math.PI) / 180);

  const getDecisionStyle = (d: string) => {
    if (d === 'APPROVE') return 'bg-ob-glass2 text-ob-ok';
    if (d === 'CONDITIONAL_APPROVE') return 'bg-ob-warn-bg text-ob-warn';
    if (d === 'REJECT' || d === 'HARD_REJECT') return 'bg-ob-warn-bg text-ob-warn';
    return 'bg-ob-glass2 text-ob-muted';
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
          stroke="var(--ob-text)"
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
          stroke="var(--ob-text)"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
        <circle cx="150" cy="150" r="5" fill="var(--ob-text)" />

        {/* Score text */}
        <text
          x="150"
          y="138"
          textAnchor="middle"
          fill="var(--ob-text)"
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
      <div className={`mt-2 px-4 py-1.5 rounded text-[11px] uppercase tracking-wider font-medium ${getDecisionStyle(decision)}`}>
        {decision.replace('_', ' ')}
      </div>
    </div>
  );
}
