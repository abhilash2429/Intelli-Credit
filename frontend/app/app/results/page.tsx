'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Bar,
  Cell,
} from 'recharts';
import {
  getExplainV1,
  getResearchV1,
  getResultsV1,
  getReportUrlV1,
  getSwotV1,
  getInvestmentReportUrl,
} from '@/lib/api';
import { formatCurrencyCr, formatPercentage, formatRatio } from '@/lib/formatters';
import { useAnalysisStore } from '@/store/analysisStore';
import FiveCsRadar from '@/components/FiveCsRadar';
import TimelineView from '@/components/TimelineView';
import ResearchFeed from '@/components/ResearchFeed';
import ShapChart from '@/components/ShapChart';
import AnomalyFlags from '@/components/AnomalyFlags';
import StressTestPanel from '@/components/StressTestPanel';
import SwotMatrix from '@/components/SwotMatrix';
import FraudGraph from '@/components/FraudGraph';

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export default function ResultsPage() {
  const [result, setResult] = useState<any>(null);
  const [explain, setExplain] = useState<any>(null);
  const [research, setResearch] = useState<any[]>([]);
  const [swot, setSwot] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [statusMessage, setStatusMessage] = useState('Loading analysis results...');
  const { companyId, uploadedFileNames, setResult: storeResult } = useAnalysisStore();

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      if (!companyId) {
        setLoading(false);
        setStatusMessage('No company selected. Please upload documents first.');
        return;
      }

      try {
        let latestResult: any = null;
        for (let i = 0; i < 120; i += 1) {
          const res = await getResultsV1(companyId);
          latestResult = res.data;
          const runStatus = String(latestResult?.status || res.status || '').toLowerCase();
          if (runStatus === 'error') {
            setStatusMessage(latestResult?.error_message || 'Analysis failed.');
            break;
          }
          if (runStatus !== 'processing' && latestResult?.decision) break;
          setStatusMessage(`Analysis in progress: ${latestResult?.current_step || 'INITIALIZING'}...`);
          await sleep(1200);
        }

        if (!cancelled) {
          setResult(latestResult);
          storeResult(latestResult);
        }

        const explainRes = await getExplainV1(companyId).catch(() => null);
        const researchRes = await getResearchV1(companyId).catch(() => null);

        if (!cancelled) {
          setExplain(explainRes?.data || null);
          setResearch(researchRes?.data || []);
        }

        // Fetch SWOT — try dedicated endpoint first, fall back to result payload
        try {
          const swotRes = await getSwotV1(companyId);
          if (!cancelled) setSwot(swotRes.data);
        } catch {
          // SWOT not in DB — check if embedded in the result payload
          const embedded = latestResult?.swot_data || latestResult?.swot || null;
          if (!cancelled && embedded) setSwot(embedded);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) setStatusMessage('Unable to load analysis yet. Retrying from pipeline is recommended.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => { cancelled = true; };
  }, [companyId, storeResult]);

  useEffect(() => {
    if (!result) return;
    const limitDebug = result?.limit_debug || {};
    const company = result?.company || {};
    const extractedData = result?.financials || result?.parsed_financials?.financials || {};
    const loanData = result?.loan || {};
    const extractedRevenue =
      limitDebug.extracted_revenue ??
      extractedData.annual_revenue_cr ??
      extractedData.revenue_cr ??
      extractedData.gross_receipts_cr;

    console.log('LIMIT DEBUG:', {
      form_turnover:
        limitDebug.form_turnover ?? company.turnover ?? company.annual_turnover_cr,
      extracted_revenue: extractedRevenue,
      requested_amount:
        limitDebug.requested_amount ?? loanData.loan_amount_cr ?? result?.decision?.recommended_loan_amount,
      using_value:
        limitDebug.using_value ??
        (extractedRevenue ? 'extracted_data.annual_revenue_cr' : 'company.turnover'),
    });
  }, [result]);

  const decision = result?.decision || {};
  const score = Number(
    decision.normalized_score ?? (decision.credit_score ? (Number(decision.credit_score) / 900) * 100 : 0)
  );
  const dueDiligence = useMemo(() => result?.due_diligence || {}, [result]);
  const borrowerContext = useMemo(() => dueDiligence?.borrower_context || {}, [dueDiligence]);
  const humanImpactPoints = Number(decision?.human_input_impact_points || 0);
  const hasBorrowerInput = useMemo(() => {
    const borrowerFields = [
      borrowerContext.borrower_finance_officer_name,
      borrowerContext.borrower_finance_officer_role,
      borrowerContext.borrower_finance_officer_email,
      borrowerContext.borrower_finance_officer_phone,
      borrowerContext.finance_officer_name,
      borrowerContext.finance_officer_role,
      borrowerContext.finance_officer_email,
      borrowerContext.finance_officer_phone,
      borrowerContext.borrower_business_highlights,
      borrowerContext.business_highlights,
      borrowerContext.borrower_major_customers,
      borrowerContext.major_customers,
      borrowerContext.borrower_contingent_liabilities,
      borrowerContext.contingent_liabilities,
      borrowerContext.borrower_planned_capex,
      borrowerContext.planned_capex,
      borrowerContext.borrower_disclosed_risks,
      borrowerContext.disclosed_risks,
    ];
    return borrowerFields.some((value) => String(value || '').trim().length > 0);
  }, [borrowerContext]);

  const anomalyFlags = useMemo(() => {
    const cv = result?.cross_validation || {};
    const anomalies = Array.isArray(cv?.anomalies) ? cv.anomalies : [];
    const fraudIndicators = Array.isArray(cv?.fraud_indicators) ? cv.fraud_indicators : [];
    const researchAlerts = Array.isArray(result?.research_alerts) ? result.research_alerts : [];
    const fraudAsFlags = fraudIndicators.map((item: any) => ({
      title: String(item?.indicator || 'Fraud indicator'),
      details: `Source: ${String(item?.source || 'unknown')}${item?.confidence != null ? ` · confidence ${Math.round(Number(item.confidence) * 100)}%` : ''}`,
      severity: String(item?.severity || 'MEDIUM'),
    }));
    const researchAsFlags = researchAlerts.map((item: any) => ({
      title: `Research Alert: ${String(item?.title || 'Critical red flag')}`,
      details: `Advisory only (does not change score). ${String(item?.summary || '')} Source: ${String(item?.source_name || 'Web')}`,
      severity: String(item?.severity || 'HIGH'),
    }));
    return [...anomalies, ...fraudAsFlags, ...researchAsFlags];
  }, [result]);

  const fiveC = useMemo(() => {
    // Use backend-computed Five Cs if available (from five_c_analyzer)
    const backendFiveC = result?.five_cs;
    if (backendFiveC) {
      return {
        character: Number(backendFiveC.character?.score ?? 5),
        capacity: Number(backendFiveC.capacity?.score ?? 5),
        capital: Number(backendFiveC.capital?.score ?? 5),
        collateral: Number(backendFiveC.collateral?.score ?? 5),
        conditions: Number(backendFiveC.conditions?.score ?? 5),
      };
    }

    // Fallback: compute from features with proper individual dimensions
    const f = result?.features || {};
    const dscr = Number(f.dscr || 1.2);
    const de = Number(f.debt_equity_ratio || 1.5);
    const mgmt = Number(f.management_integrity_score || 6);
    const fraudNews = Number(f.has_promoter_fraud_news || 0);
    const struckOff = Number(f.has_mca_struck_off_associates || 0);
    const colCov = Number(f.collateral_coverage_ratio || 1.1);
    const colType = Number(f.collateral_type_score || 5);
    const headwinds = Number(f.has_sector_headwinds || 0);
    const revInflation = Number(f.has_revenue_inflation_signals || 0);
    const icr = Number(f.interest_coverage_ratio || 2);
    const capacity_util = Number(f.factory_capacity_utilization || 60);
    const cr = Number(f.current_ratio || 1.3);

    return {
      character: Math.min(10, Math.max(1, 10 - fraudNews * 4 - struckOff * 3 - (mgmt < 5 ? 2 : 0))),
      capacity: Math.min(10, Math.max(1, dscr * 3 + icr + capacity_util / 20)),
      capital: Math.min(10, Math.max(1, 9 - de + cr)),
      collateral: Math.min(10, Math.max(1, colCov * 4 + colType / 2)),
      conditions: Math.min(10, Math.max(1, 8 - headwinds * 2.5 - revInflation * 2)),
    };
  }, [result]);

  const gstBankData = useMemo(() => {
    // Use monthly GST data from XLSX if available
    const monthlyData = result?.gst_xlsx_data?.monthly_data || [];
    if (monthlyData.length > 0) {
      return monthlyData.map((m: any) => ({
        month: String(m.month || '').replace(/\s+/g, ' ').trim() || 'Unknown',
        gst: Number(m.outward_supplies || 0),
        bank: Number(m.bank_credits || m.outward_supplies || 0) * 0.92, // approximate bank credits
      }));
    }

    // Fallback: generate 12 month labels with proportional data
    const fy = result?.gst_xlsx_data?.fiscal_year || 'FY2023-24';
    const fyMatch = fy.match(/(\d{4})/);
    const startYear = fyMatch ? Number(fyMatch[1]) : 2023;
    const monthLabels = [
      `Apr-${String(startYear).slice(2)}`, `May-${String(startYear).slice(2)}`,
      `Jun-${String(startYear).slice(2)}`, `Jul-${String(startYear).slice(2)}`,
      `Aug-${String(startYear).slice(2)}`, `Sep-${String(startYear).slice(2)}`,
      `Oct-${String(startYear).slice(2)}`, `Nov-${String(startYear).slice(2)}`,
      `Dec-${String(startYear).slice(2)}`, `Jan-${String(startYear + 1).slice(2)}`,
      `Feb-${String(startYear + 1).slice(2)}`, `Mar-${String(startYear + 1).slice(2)}`,
    ];
    const itcGap = Number(result?.gst_mismatch?.itc_inflation_percentage || 0);
    return monthLabels.map((label) => ({
      month: label,
      gst: 100 + itcGap,
      bank: 100,
    }));
  }, [result]);

  if (loading) {
    return (
      <div className="bg-ob-bg py-10 px-8 min-h-[calc(100vh-56px)]">
        <p className="text-ob-muted animate-pulse">{statusMessage}</p>
      </div>
    );
  }

  if (!result || !decision?.credit_score) {
    return (
      <div className="bg-ob-bg py-10 px-8 min-h-[calc(100vh-56px)]">
        <p className="text-ob-muted">{statusMessage || 'Results are being prepared. Please keep this page open.'}</p>
      </div>
    );
  }

  const chartTooltipStyle = {
    backgroundColor: 'var(--ob-surface)',
    border: '1px solid var(--ob-edge)',
    color: 'var(--ob-text)',
    borderRadius: '8px',
  };

  return (
    <div className="bg-ob-bg py-10 px-4 md:px-8">
      <div className="max-w-[1200px] mx-auto">
        {/* CSS Grid layout */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          {/* Score summary — spans 2 cols */}
          <div className="xl:col-span-2 bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Analysis Results</p>
            <div className="flex flex-wrap gap-4 items-baseline">
              <span className="font-display text-[32px] text-ob-text">{score.toFixed(0)}</span>
              <span className="text-ob-muted text-[14px]">/ 100</span>
              <span className="font-mono text-[13px] bg-ob-glass2 text-ob-text px-2 py-0.5 rounded">{decision.risk_grade}</span>
              <span className="font-mono text-[13px] bg-ob-glass2 text-ob-ok px-2 py-0.5 rounded">{decision.recommendation}</span>
            </div>
            <p className="text-ob-muted text-[13px] mt-2">
              {decision.recommendation === 'REJECT' ? (
                <>
                  Recommended: <span className="font-mono text-ob-warn">Not Sanctioned (Requested: {formatCurrencyCr(Number(decision.recommended_loan_amount || 0))})</span>
                  {' · '}Interest: <span className="font-mono text-ob-muted">N/A</span>
                </>
              ) : (
                <>
                  Recommended: <span className="font-mono text-ob-text">{formatCurrencyCr(Number(decision.recommended_loan_amount || 0))}</span>
                  {' · '}Interest: <span className="font-mono text-ob-text">{Number(decision.recommended_interest_rate || 0).toFixed(2)}%</span>
                </>
              )}
            </p>
            <div className="flex flex-wrap gap-4 mt-2 text-[12px]">
              <span className="text-ob-muted">
                Model Confidence: <span className="font-mono font-medium text-ob-text">
                  {result?.model_confidence || 'N/A'}
                </span>
              </span>
              <span className="text-ob-muted">
                Human input: <span className={`font-mono font-medium ${humanImpactPoints >= 0 ? 'text-ob-ok' : 'text-ob-warn'}`}>
                  {humanImpactPoints >= 0 ? '+' : ''}{humanImpactPoints.toFixed(1)} pts
                </span>
              </span>
              <span className="text-ob-muted">
                Borrower input: <span className={`font-medium ${hasBorrowerInput ? 'text-ob-ok' : 'text-ob-warn'}`}>
                  {hasBorrowerInput ? 'Captured' : 'Not provided'}
                </span>
              </span>
            </div>
            {result?.cam_docx_path && (
              <>
              <a
                href={getReportUrlV1(companyId)}
                className="inline-block mt-[12px] px-[24px] py-[10px] rounded-[6px] bg-ob-text text-ob-bg text-[13px] font-body font-bold no-underline hover:bg-ob-cream transition-all"
              >
                Download CAM (.docx)
              </a>
              <a
                href={getInvestmentReportUrl(companyId)}
                className="inline-block mt-2 ml-2 px-[24px] py-[10px] rounded-[6px] bg-ob-glass2 border border-ob-edge text-ob-text text-[13px] font-body font-bold no-underline hover:bg-ob-glass transition-all"
              >
                Investment Report (.docx)
              </a>
              </>
            )}
          </div>

          {/* Anomaly flags */}
          <div className="xl:col-span-1">
            <AnomalyFlags anomalies={anomalyFlags} />
          </div>

          {/* Five Cs Radar + GST chart — spans 2 cols */}
          <div className="xl:col-span-2 space-y-5">
            <FiveCsRadar company={fiveC} />

            <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
              <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">GST vs Bank Reconciliation</p>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={gstBankData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--ob-edge)" />
                  <XAxis dataKey="month" tick={{ fill: 'var(--ob-muted)', fontSize: 12, fontFamily: 'DM Mono' }} />
                  <YAxis tick={{ fill: 'var(--ob-muted)', fontSize: 12, fontFamily: 'DM Mono' }} />
                  <Tooltip contentStyle={chartTooltipStyle} />
                  <Bar dataKey="gst" name="GST Reported Revenue" fill="var(--ob-text)">
                    {gstBankData.map((item: { gst: number; bank: number }, idx: number) => (
                      <Cell key={idx} fill={item.gst - item.bank > 5 ? 'var(--ob-warn)' : 'var(--ob-text)'} />
                    ))}
                  </Bar>
                  <Bar dataKey="bank" name="Bank Credits Received" fill="var(--ob-edge2)" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* SHAP + Timeline */}
            <ShapChart
              data={Object.entries(explain?.shap_waterfall_data || {}).map(([feature, value]) => ({
                feature,
                value: Number(value),
                direction: Number(value) > 0 ? 'positive' : 'negative',
              }))}
            />

            <StressTestPanel baseScore={score} />

            {/* SWOT Analysis */}
            {swot && (
              <SwotMatrix
                strengths={swot.strengths || []}
                weaknesses={swot.weaknesses || []}
                opportunities={swot.opportunities || []}
                threats={swot.threats || []}
                investmentThesis={swot.investment_thesis}
                recommendation={swot.recommendation}
                sectorOutlook={swot.sector_outlook}
              />
            )}
          </div>

          {/* Right sidebar — sticky */}
          <div className="xl:col-span-1 space-y-5 xl:sticky xl:top-[72px] xl:self-start">
            {/* Human input traceability */}
            <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
              <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Human Input Traceability</p>
              {hasBorrowerInput ? (
                <div className="space-y-2 text-[12px]">
                  <p className="text-ob-muted">Finance officer: <span className="text-ob-text font-medium">{String(borrowerContext.finance_officer_name || 'N/A')}</span></p>
                  <p className="text-ob-muted">Cooperation: <span className="text-ob-text font-medium">{String(borrowerContext.management_cooperation || 'N/A')}</span></p>
                  <p className="text-ob-muted">Capacity: <span className="font-mono text-ob-text">{formatPercentage(Number(dueDiligence.factory_capacity_utilization || 0))}</span></p>
                  <p className="text-ob-muted">Integrity: <span className="font-mono text-ob-text">{formatRatio(Number(dueDiligence.management_integrity_score || 0), 1, '/10')}</span></p>
                </div>
              ) : (
                <p className="text-ob-muted text-[12px]">
                  No borrower clarifications captured. Expected any of: finance officer details, business highlights,
                  major customers, contingent liabilities, planned capex, or disclosed risks.
                </p>
              )}
            </div>

            {/* Documents card */}
            {uploadedFileNames.length > 0 && (
              <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
                <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Documents</p>
                <div className="space-y-1.5">
                  {uploadedFileNames.map((name, i) => (
                    <div key={i} className="flex items-center gap-2 text-[12px]">
                      <span className="w-1.5 h-1.5 rounded-full bg-ob-ok flex-shrink-0" />
                      <span className="font-mono text-ob-text truncate">{name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <TimelineView
              items={(result?.audit_events || []).map((a: any) => ({
                timestamp: a.timestamp,
                title: a.message,
                severity: a.severity || 'INFORMATIONAL',
                details: a.step,
              }))}
            />

            <ResearchFeed findings={research} />
          </div>
        </div>

        {/* Full width: Fraud Graph — dynamic from analysis data */}
        <div className="mt-5">
          {result?.fraud_graph?.nodes?.length > 0 ? (
            <FraudGraph
              nodes={result.fraud_graph.nodes}
              links={result.fraud_graph.links || []}
              weakAssociations={result.fraud_graph.weak_associations || []}
              entityCount={result.fraud_graph.entity_count}
              connectionCount={result.fraud_graph.connection_count}
            />
          ) : (
            <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
              <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Fraud Fingerprinting Graph</p>
              <p className="text-ob-muted text-[13px]">No confirmed fraud network connections detected (requires 2+ corroborating signals).</p>
              {result?.fraud_graph?.weak_associations?.length > 0 && (
                <details className="mt-3">
                  <summary className="text-[11px] text-ob-muted cursor-pointer">Show weak associations (unverified)</summary>
                  <div className="mt-2 space-y-1">
                    {result.fraud_graph.weak_associations.map((a: any, idx: number) => (
                      <p key={idx} className="text-[11px] text-ob-muted font-mono">{a.entity} — {a.signal} (LOW confidence)</p>
                    ))}
                  </div>
                </details>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
