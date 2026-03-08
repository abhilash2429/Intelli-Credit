'use client';

import { useEffect, useState } from 'react';
import { useAnalysisStore } from '@/store/analysisStore';
import { getExplainV1 } from '@/lib/api';
import ShapChart from '@/components/ShapChart';
import FraudGraph from '@/components/FraudGraph';

const INDIA_TOOLTIPS: Record<string, string> = {
  GSTR2A: 'Auto-populated purchase data from supplier filings. Usually hard to manipulate at buyer side.',
  DSCR: 'Debt Service Coverage Ratio = cash available for debt service / debt obligations.',
  SARFAESI: 'Indian law enabling secured creditors to enforce security interests without court intervention.',
  NCLT: 'National Company Law Tribunal; handles insolvency and corporate disputes.',
  CIRP: 'Corporate Insolvency Resolution Process under Insolvency and Bankruptcy Code.',
};

export default function ExplainPage() {
  const [explain, setExplain] = useState<any>(null);
  const { companyId } = useAnalysisStore();

  useEffect(() => {
    if (!companyId) return;
    getExplainV1(companyId).then((res) => setExplain(res.data)).catch(console.error);
  }, [companyId]);

  const shapData = Object.entries(explain?.shap_waterfall_data || {}).map(([feature, value]) => ({
    feature,
    value: Number(value),
    direction: Number(value) > 0 ? 'positive' : 'negative',
  }));

  return (
    <div className="bg-ic-page py-10 px-4 md:px-8">
      <div className="max-w-[1100px] mx-auto flex flex-col lg:flex-row gap-5">
        {/* Left column — 55% */}
        <div className="flex-[55] space-y-5">
          <h1 className="font-display text-[26px] font-normal text-ic-text">What drove this score?</h1>

          {/* Decision Narrative */}
          <div className="bg-ic-surface border border-ic-border rounded-[10px] p-5">
            <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ic-muted mb-2.5">Decision Narrative</p>
            <p className="text-ic-text text-[14px] whitespace-pre-wrap leading-relaxed">
              {explain?.decision_narrative || 'No explanation found yet.'}
            </p>
          </div>

          {/* SHAP Chart */}
          {shapData.length > 0 && <ShapChart data={shapData} />}

          {/* Fraud Graph (if applicable) */}
          <FraudGraph
            nodes={[
              { id: 'Company', type: 'company' },
              { id: 'Entity B', type: 'counterparty' },
              { id: 'Entity C', type: 'counterparty' },
            ]}
            links={[
              { source: 'Company', target: 'Entity B', value: 40 },
              { source: 'Entity B', target: 'Entity C', value: 38 },
              { source: 'Entity C', target: 'Company', value: 39 },
            ]}
          />
        </div>

        {/* Right column — 45% */}
        <div className="flex-[45] space-y-5">
          {/* Positive Factors */}
          <div className="bg-ic-surface border border-ic-border rounded-[10px] p-5">
            <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ic-muted mb-2.5">Top Positive Factors</p>
            <ul className="space-y-2">
              {(explain?.top_positive_factors || []).map((f: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-[13px]">
                  <span className="w-2 h-2 rounded-full bg-ic-positive mt-1.5 flex-shrink-0" />
                  <span className="text-ic-text">{f}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Negative Factors */}
          <div className="bg-ic-surface border border-ic-border rounded-[10px] p-5">
            <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ic-muted mb-2.5">Top Risk Factors</p>
            <ul className="space-y-2">
              {(explain?.top_negative_factors || []).map((f: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-[13px]">
                  <span className="w-2 h-2 rounded-full bg-ic-warning mt-1.5 flex-shrink-0" />
                  <span className="text-ic-text">{f}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Model Confidence */}
          <div className="bg-ic-surface border border-ic-border rounded-[10px] p-5">
            <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ic-muted mb-2.5">Model Confidence</p>
            <p className="font-mono text-[28px] text-ic-text">
              {explain?.model_confidence ? `${(Number(explain.model_confidence) * 100).toFixed(0)}%` : 'N/A'}
            </p>
            <p className="text-[13px] text-ic-muted mt-2 leading-relaxed">
              Confidence is derived from the agreement between rule-based and ML scoring components.
            </p>
          </div>

          {/* India Context Tooltips */}
          <div className="bg-ic-surface border border-ic-border rounded-[10px] p-5">
            <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ic-muted mb-2.5">India Context</p>
            <div className="space-y-3">
              {Object.entries(INDIA_TOOLTIPS).map(([term, meaning]) => (
                <div key={term} className="p-2.5 rounded-md bg-ic-surface-mid">
                  <p className="text-[12px] font-medium text-ic-accent">{term}</p>
                  <p className="text-[12px] text-ic-muted mt-0.5">{meaning}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
