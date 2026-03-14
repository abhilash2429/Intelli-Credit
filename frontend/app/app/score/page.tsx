'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAnalysisStore } from '@/store/analysisStore';
import { getResultsV1 } from '@/lib/api';
import RiskGauge from '@/components/RiskGauge';
import ShapChart from '@/components/ShapChart';

export default function ScorePage() {
  const { result, companyId, setResult } = useAnalysisStore();
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (companyId && (!result || !result.decision)) {
      setLoading(true);
      getResultsV1(companyId)
        .then((res) => setResult(res.data))
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [companyId, result, setResult]);

  // Extract score data from the v1 result payload stored after Results page loads
  const score = useMemo(() => {
    if (!result) return null;
    const decision = result.decision || {};
    const explanation = result.explanation || {};
    const creditScore = Number(decision.credit_score || 0);
    if (!creditScore) return null;

    return {
      final_risk_score: creditScore,
      risk_category: String(decision.risk_grade || decision.risk_category || 'N/A'),
      decision: String(decision.recommendation || 'N/A'),
      rule_based_score: Number(result.rule_based_score ?? creditScore),
      ml_stress_probability: Number(result.ml_stress_probability ?? 0),
      recommended_limit_crore: Number(decision.recommended_loan_amount || 0),
      interest_premium_bps: Number(
        decision.recommended_interest_rate
          ? Math.round(decision.recommended_interest_rate * 100)
          : 0
      ),
      decision_rationale: String(
        explanation.decision_narrative || decision.decision_rationale || ''
      ),
      rule_violations: Array.isArray(result.rule_violations) ? result.rule_violations : [],
      risk_strengths: Array.isArray(result.risk_strengths) ? result.risk_strengths : [],
    };
  }, [result]);

  const shap = useMemo(() => {
    const raw = result?.explanation?.shap_waterfall_data || {};
    return Object.entries(raw).map(([feature, value]) => ({
      feature,
      value: Number(value),
      direction: Number(value) > 0 ? 'positive' : 'negative',
    }));
  }, [result]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-56px)] bg-ob-bg">
        <p className="text-ob-muted animate-pulse">Loading score data...</p>
      </div>
    );
  }

  if (!result || !result.decision) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-56px)] bg-ob-bg">
        <div className="text-center space-y-3">
          <p className="text-ob-muted text-base">Score not yet available.</p>
          <p className="text-ob-dim text-[13px]">
            Run the analysis pipeline first — navigate to{' '}
            <button onClick={() => router.push('/app/results')} className="text-ob-text underline">
              Results
            </button>{' '}
            to trigger and wait for completion.
          </p>
        </div>
      </div>
    );
  }

  if (!score) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-56px)] bg-ob-bg">
        <div className="text-center space-y-3">
          <p className="text-ob-warn text-base">Score not available.</p>
          <p className="text-ob-dim text-[13px]">
            The analysis may still be in progress. Visit the{' '}
            <button onClick={() => router.push('/app/results')} className="text-ob-text underline">
              Results
            </button>{' '}
            tab and wait for completion.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-ob-bg py-10 px-4 md:px-8">
      <div className="max-w-[1100px] mx-auto flex flex-col lg:flex-row gap-5">
        <div className="flex-[2] space-y-5">
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px] flex flex-col items-center">
            <RiskGauge score={score.final_risk_score} decision={score.decision} category={score.risk_category} />
            <p className="font-display text-[64px] font-normal text-ob-text mt-4 leading-none">{score.final_risk_score?.toFixed(1)}</p>
            <span className="mt-2 inline-block px-3 py-1 bg-ob-glass2 text-ob-text text-[11px] uppercase tracking-wider font-medium rounded">{score.risk_category}</span>
            <p className="text-[13px] text-ob-muted mt-4 text-center leading-relaxed max-w-sm">
              {score.decision_rationale
                ? score.decision_rationale.slice(0, 200) + (score.decision_rationale.length > 200 ? '...' : '')
                : 'Risk assessment computed based on financial, regulatory, and qualitative inputs.'}
            </p>
          </div>
        </div>
        <div className="flex-[3] space-y-5">
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Key Financials</p>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-ob-glass2 border border-ob-edge rounded-[8px]">
                <p className="font-mono text-[10px] text-ob-muted uppercase tracking-[0.04em]">Recommended Limit</p>
                <p className="font-mono text-xl font-medium text-ob-text mt-1">₹{score.recommended_limit_crore?.toFixed(1)} Cr</p>
              </div>
              <div className="text-center p-3 bg-ob-glass2 border border-ob-edge rounded-[8px]">
                <p className="font-mono text-[10px] text-ob-muted uppercase tracking-[0.04em]">Interest Premium</p>
                <p className="font-mono text-xl font-medium text-ob-text mt-1">+{score.interest_premium_bps} bps</p>
              </div>
              <div className="text-center p-3 bg-ob-glass2 border border-ob-edge rounded-[8px]">
                <p className="font-mono text-[10px] text-ob-muted uppercase tracking-[0.04em]">Rule Score</p>
                <p className="font-mono text-xl font-medium text-ob-text mt-1">{score.rule_based_score?.toFixed(1)}</p>
              </div>
              <div className="text-center p-3 bg-ob-glass2 border border-ob-edge rounded-[8px]">
                <p className="font-mono text-[10px] text-ob-muted uppercase tracking-[0.04em]">ML Stress Prob.</p>
                <p className="font-mono text-xl font-medium text-ob-text mt-1">{(score.ml_stress_probability * 100)?.toFixed(1)}%</p>
              </div>
            </div>
          </div>
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Rule Violations</p>
            {score.rule_violations?.length
              ? <ul className="space-y-2">{score.rule_violations.map((v: string, i: number) => <li key={i} className="text-ob-warn text-[13px] flex gap-2"><span>•</span> {v}</li>)}</ul>
              : <p className="text-ob-muted text-[13px]">No violations found.</p>}
          </div>
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Risk Strengths</p>
            {score.risk_strengths?.length
              ? <ul className="space-y-2">{score.risk_strengths.map((s: string, i: number) => <li key={i} className="text-ob-ok text-[13px] flex gap-2"><span>•</span> {s}</li>)}</ul>
              : <p className="text-ob-muted text-[13px]">No strengths identified.</p>}
          </div>
          <div className="flex flex-wrap gap-3">
            <button onClick={() => router.push('/app/results')} className="py-[12px] px-[24px] bg-transparent border border-ob-edge text-ob-muted font-body font-normal rounded-[6px] text-[13px] transition-all hover:border-ob-edge2 hover:text-ob-text">View Full Results →</button>
            <button onClick={() => router.push('/app/chat')} className="py-[12px] px-[24px] bg-ob-glass2 border border-ob-edge text-ob-text font-body font-normal rounded-[6px] text-[13px] transition-all hover:bg-ob-glass hover:border-ob-edge2">Chat with AI →</button>
            <button onClick={() => router.push('/app/cam')} className="py-[12px] px-[24px] bg-ob-text text-ob-bg font-body font-bold rounded-[6px] text-[13px] transition-all hover:bg-ob-cream">Export Memo →</button>
          </div>
        </div>
      </div>
      {shap.length > 0 && (
        <div className="max-w-[1100px] mx-auto mt-5">
          <ShapChart data={shap} />
        </div>
      )}
      {score.decision_rationale && (
        <div className="max-w-[1100px] mx-auto mt-5">
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Decision Rationale</p>
            <p className="text-ob-text text-[14px] whitespace-pre-wrap leading-relaxed font-body font-light">{score.decision_rationale}</p>
          </div>
        </div>
      )}
    </div>
  );
}
