'use client';

import { useEffect, useState } from 'react';
import { useAnalysisStore } from '@/store/analysisStore';
import { getExplainV1, getResultsV1 } from '@/lib/api';
import ShapChart from '@/components/ShapChart';
import FraudGraph from '@/components/FraudGraph';
import { useMemo } from 'react';

const INDIA_TOOLTIPS: Record<string, string> = {
  GSTR2A: 'Auto-populated purchase data from supplier filings. Usually hard to manipulate at buyer side.',
  DSCR: 'Debt Service Coverage Ratio = cash available for debt service / debt obligations.',
  SARFAESI: 'Indian law enabling secured creditors to enforce security interests without court intervention.',
  NCLT: 'National Company Law Tribunal; handles insolvency and corporate disputes.',
  CIRP: 'Corporate Insolvency Resolution Process under Insolvency and Bankruptcy Code.',
};

export default function ExplainPage() {
  const [explain, setExplain] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const { companyId, result, setResult } = useAnalysisStore();

  useEffect(() => {
    if (!companyId) return;

    // Fetch explanation payload
    getExplainV1(companyId).then((res) => setExplain(res.data)).catch(console.error);

    // Fetch full results payload if missing in store (e.g. hard refresh)
    if (!result || !result.decision) {
      setLoading(true);
      getResultsV1(companyId)
        .then((res: any) => setResult(res.data))
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [companyId, result, setResult]);

  const fraudNodes = useMemo(() => result?.fraud_graph?.nodes || [], [result]);
  const fraudLinks = useMemo(() => result?.fraud_graph?.links || [], [result]);
  const weakAssociations = useMemo(() => result?.fraud_graph?.weak_associations || [], [result]);
  const fraudEntityCount = useMemo(() => result?.fraud_graph?.entity_count, [result]);
  const fraudConnectionCount = useMemo(() => result?.fraud_graph?.connection_count, [result]);

  const shapData = Object.entries(explain?.shap_waterfall_data || {}).map(([feature, value]) => ({
    feature,
    value: Number(value),
    direction: Number(value) > 0 ? 'positive' : 'negative',
  }));

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-56px)] bg-ob-bg">
        <p className="text-ob-muted animate-pulse">Loading explanation data...</p>
      </div>
    );
  }

  return (
    <div className="bg-ob-bg py-10 px-4 md:px-8">
      <div className="max-w-[1100px] mx-auto flex flex-col lg:flex-row gap-5">
        {/* Left column — 55% */}
        <div className="flex-[55] space-y-5">
          <h1 className="font-display text-[26px] font-normal text-ob-text">What drove this score?</h1>

          {/* Decision Narrative */}
          <div className="bg-ob-surface border border-ob-edge rounded-[10px] p-5">
            <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ob-muted mb-2.5">Decision Narrative</p>
            <p className="text-ob-text text-[14px] whitespace-pre-wrap leading-relaxed">
              {explain?.decision_narrative || 'No explanation found yet.'}
            </p>
          </div>

          {/* SHAP Chart */}
          {shapData.length > 0 && <ShapChart data={shapData} />}

          {/* Fraud Graph — only shown if real data exists */}
          {fraudNodes.length > 0 && (
            <FraudGraph
              nodes={fraudNodes}
              links={fraudLinks}
              weakAssociations={weakAssociations}
              entityCount={fraudEntityCount}
              connectionCount={fraudConnectionCount}
            />
          )}
        </div>

        {/* Right column — 45% */}
        <div className="flex-[45] space-y-5">
          {/* Positive Factors */}
          <div className="bg-ob-surface border border-ob-edge rounded-[10px] p-5">
            <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ob-muted mb-2.5">Top Positive Factors</p>
            <ul className="space-y-2">
              {(explain?.top_positive_factors || []).map((f: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-[13px]">
                  <span className="w-2 h-2 rounded-full bg-ob-ok mt-1.5 flex-shrink-0" />
                  <span className="text-ob-text">{f}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Negative Factors */}
          <div className="bg-ob-surface border border-ob-edge rounded-[10px] p-5">
            <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ob-muted mb-2.5">Top Risk Factors</p>
            <ul className="space-y-2">
              {(explain?.top_negative_factors || []).map((f: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-[13px]">
                  <span className="w-2 h-2 rounded-full bg-ob-warn mt-1.5 flex-shrink-0" />
                  <span className="text-ob-text">{f}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Model Confidence */}
          <div className="bg-ob-surface border border-ob-edge rounded-[10px] p-5">
            <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ob-muted mb-2.5">Model Confidence</p>
            <p className="font-mono text-[28px] text-ob-text">
              {explain?.confidence_in_decision 
                ? `${(Number(explain.confidence_in_decision) * 100).toFixed(0)}%`
                : result?.model_confidence_pct
                ? `${Number(result.model_confidence_pct).toFixed(0)}%`
                : 'N/A'}
            </p>
            <p className="text-[13px] text-ob-muted mt-2 leading-relaxed">
              Confidence is derived from the agreement between rule-based and ML scoring components.
            </p>
          </div>

          {/* India Context Tooltips */}
          <div className="bg-ob-surface border border-ob-edge rounded-[10px] p-5">
            <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ob-muted mb-2.5">India Context</p>
            <div className="space-y-3">
              {Object.entries(INDIA_TOOLTIPS).map(([term, meaning]) => (
                <div key={term} className="p-2.5 rounded-md bg-ob-surface2">
                  <p className="text-[12px] font-medium text-ob-text">{term}</p>
                  <p className="text-[12px] text-ob-muted mt-0.5">{meaning}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
