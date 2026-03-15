'use client';

import { useMemo, useState } from 'react';

type StressScenarioResult = {
  stressed_score: number;
  stressed_decision: 'APPROVE' | 'CONDITIONAL APPROVE' | 'REJECT';
  score_reduction: number;
  ebitda_impact_pct: number;
  narrative: string;
};

function applyStressScenario(revenueDropPct: number, baseScore: number): StressScenarioResult {
  // Revenue drop impacts EBITDA proportionally
  // Assume EBITDA margin stays same, so revenue drop = EBITDA drop
  const ebitdaImpact = revenueDropPct * 0.8; // 80% pass-through
  const dscrImpact = revenueDropPct * 0.6; // DSCR sensitivity (kept for transparency)

  // Score reduction: each 10% revenue drop = ~8 point score drop
  const scoreReduction = (revenueDropPct / 10) * 8;
  const stressedScore = Math.max(0, Math.min(100, baseScore - scoreReduction));

  // Determine if decision changes
  let stressedDecision: StressScenarioResult['stressed_decision'];
  if (stressedScore >= 75) stressedDecision = 'APPROVE';
  else if (stressedScore >= 50) stressedDecision = 'CONDITIONAL APPROVE';
  else stressedDecision = 'REJECT';

  return {
    stressed_score: Math.round(stressedScore),
    stressed_decision: stressedDecision,
    score_reduction: Math.round(scoreReduction),
    ebitda_impact_pct: ebitdaImpact,
    narrative: `A ${revenueDropPct}% revenue decline would reduce the credit score from ${Math.round(
      baseScore
    )} to ${Math.round(stressedScore)}/100, resulting in ${stressedDecision}. DSCR sensitivity impact proxy: ${dscrImpact.toFixed(
      1
    )}%.`,
  };
}

export default function StressTestPanel({
  baseScore,
  onSimulate,
}: {
  baseScore: number;
  onSimulate?: (dropPct: number) => void;
}) {
  const [revenueDrop, setRevenueDrop] = useState(20);
  const [scenario, setScenario] = useState<StressScenarioResult | null>(null);

  const clampedBaseScore = useMemo(() => Math.max(0, Math.min(100, Number(baseScore || 0))), [baseScore]);

  const previewScenario = useMemo(
    () => applyStressScenario(revenueDrop, clampedBaseScore),
    [revenueDrop, clampedBaseScore]
  );

  const decisionStyle = (decision: string) => {
    if (decision === 'APPROVE') {
      return { backgroundColor: 'rgba(34,197,94,0.14)', color: '#22c55e', borderColor: 'rgba(34,197,94,0.35)' };
    }
    if (decision === 'CONDITIONAL APPROVE') {
      return { backgroundColor: 'rgba(234,179,8,0.14)', color: '#eab308', borderColor: 'rgba(234,179,8,0.35)' };
    }
    return { backgroundColor: 'rgba(239,68,68,0.14)', color: '#ef4444', borderColor: 'rgba(239,68,68,0.35)' };
  };

  return (
    <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
      <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Stress Test</p>
      <p className="text-ob-text text-[14px] mb-3">
        What if revenue drops by <span className="font-mono font-medium">{revenueDrop}%</span>?
      </p>
      <input
        type="range"
        min={0}
        max={40}
        value={revenueDrop}
        onChange={(e) => setRevenueDrop(Number(e.target.value))}
        className="w-full"
      />
      <p className="text-ob-text text-[14px] mt-3">
        Simulated Credit Score:{' '}
        <span className="font-mono font-medium">{(scenario?.stressed_score ?? previewScenario.stressed_score).toFixed(0)}</span>
        <span className="text-ob-muted"> / 100</span>
      </p>
      <p className="text-ob-muted text-[12px] mt-1">
        Score reduction: {scenario?.score_reduction ?? previewScenario.score_reduction} points | EBITDA impact:{' '}
        {(scenario?.ebitda_impact_pct ?? previewScenario.ebitda_impact_pct).toFixed(1)}%
      </p>
      <button
        type="button"
        onClick={() => {
          const result = applyStressScenario(revenueDrop, clampedBaseScore);
          setScenario(result);
          onSimulate?.(revenueDrop);
        }}
        className="mt-3 px-4 py-2 rounded-[6px] bg-ob-text text-ob-bg font-bold text-[12px] transition-colors hover:bg-ob-cream"
      >
        Apply Scenario
      </button>
      {(scenario || previewScenario) && (
        <div className="mt-3">
          <span
            className="inline-flex border rounded px-2 py-1 text-[11px] font-mono tracking-wide"
            style={decisionStyle((scenario?.stressed_decision ?? previewScenario.stressed_decision) || 'REJECT')}
          >
            {(scenario?.stressed_decision ?? previewScenario.stressed_decision) || 'REJECT'}
          </span>
          {scenario && <p className="text-ob-muted text-[12px] mt-2 leading-relaxed">{scenario.narrative}</p>}
        </div>
      )}
    </div>
  );
}
