'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAnalysisStore } from '@/store/analysisStore';
import { createCompanyV1, createLoanApplication } from '@/lib/api';

const SECTORS = [
  'NBFC', 'Manufacturing', 'Real Estate', 'Infrastructure',
  'IT / Software', 'Pharma', 'FMCG', 'Textiles',
  'Agriculture', 'Steel', 'Telecom', 'Aviation', 'Other',
];

const LOAN_TYPES = [
  'Term Loan', 'Working Capital', 'Letter of Credit', 'Bank Guarantee',
  'Cash Credit', 'Overdraft', 'Project Finance', 'Other',
];

const REPAYMENT_MODES = ['Monthly', 'Quarterly', 'Half-Yearly', 'Bullet'];

export default function StartPage() {
  const router = useRouter();
  const { setCompany, setPipelineStep } = useAnalysisStore();
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Step 1: Entity
  const [entity, setEntity] = useState({
    name: '', cin: '', pan: '', gstin: '', sector: '',
    annual_turnover_cr: '', employee_count: '', year_of_incorporation: '', registered_address: '',
  });

  // Step 2: Loan
  const [loan, setLoan] = useState({
    loan_type: '', loan_amount_cr: '', tenure_months: '',
    proposed_rate_pct: '', repayment_mode: '', purpose: '',
    collateral_type: '', collateral_value_cr: '',
  });

  const canAdvance1 = entity.name.trim() && entity.sector;
  const canAdvance2 = loan.loan_type && Number(loan.loan_amount_cr) > 0 && Number(loan.tenure_months) > 0;

  const handleSubmit = async () => {
    setSubmitting(true);
    setError('');
    try {
      // Create company
      const companyRes = await createCompanyV1({
        name: entity.name.trim(),
        cin: entity.cin || undefined,
        sector: entity.sector,
        loan_amount_requested: Number(loan.loan_amount_cr) || 0,
        loan_tenor_months: Number(loan.tenure_months) || 0,
        loan_purpose: loan.purpose || undefined,
      });
      const companyId = companyRes.data?.company_id;
      if (!companyId) throw new Error('No company ID returned');

      // Create loan application
      await createLoanApplication({
        company_id: companyId,
        loan_type: loan.loan_type,
        loan_amount_cr: Number(loan.loan_amount_cr),
        tenure_months: Number(loan.tenure_months),
        proposed_rate_pct: Number(loan.proposed_rate_pct) || undefined,
        repayment_mode: loan.repayment_mode || undefined,
        purpose: loan.purpose || undefined,
        collateral_type: loan.collateral_type || undefined,
        collateral_value_cr: Number(loan.collateral_value_cr) || undefined,
      });

      document.cookie = 'ic_session=1; path=/; max-age=86400';
      setCompany(companyId, entity.name.trim());
      setPipelineStep(0);
      router.push('/app/upload');
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  const inputCls = 'w-full h-[44px] px-3 bg-ob-glass2 border border-ob-edge rounded-[6px] text-ob-text text-[13px] placeholder:text-ob-muted/60 focus:outline-none focus:ring-1 focus:ring-ob-text/40 transition-all';
  const labelCls = 'block text-[11px] text-ob-muted font-mono uppercase tracking-[0.08em] mb-1';

  return (
    <div className="min-h-screen bg-ob-bg flex items-center justify-center px-4 pt-[60px] pb-10">
      <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-8 max-w-[560px] w-full backdrop-blur-[28px]">
        {/* Progress */}
        <div className="flex items-center gap-2 mb-6">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-mono transition-all ${
                s === step ? 'bg-ob-text text-ob-bg font-bold' :
                s < step ? 'bg-ob-ok/20 text-ob-ok' : 'bg-ob-glass2 text-ob-dim'
              }`}>{s < step ? '✓' : s}</div>
              {s < 3 && <div className={`w-8 h-[1px] ${s < step ? 'bg-ob-ok/40' : 'bg-ob-edge'}`} />}
            </div>
          ))}
          <span className="ml-3 font-mono text-[10px] text-ob-muted tracking-[0.12em] uppercase">
            {step === 1 ? 'Entity Profile' : step === 2 ? 'Loan Details' : 'Review & Submit'}
          </span>
        </div>

        {/* Step 1: Entity */}
        {step === 1 && (
          <div className="space-y-4">
            <h1 className="font-display text-[24px] text-ob-text">Entity Profile</h1>
            <p className="text-[12px] text-ob-muted">Tell us about the company being assessed.</p>
            <div>
              <label className={labelCls}>Company Name *</label>
              <input className={inputCls} value={entity.name} onChange={(e) => setEntity({ ...entity, name: e.target.value })} placeholder="e.g. Vardhman Agri Processing Pvt. Ltd." />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>CIN</label>
                <input className={inputCls} value={entity.cin} onChange={(e) => setEntity({ ...entity, cin: e.target.value })} placeholder="U12345MH2020PTC123456" />
              </div>
              <div>
                <label className={labelCls}>PAN</label>
                <input className={inputCls} value={entity.pan} onChange={(e) => setEntity({ ...entity, pan: e.target.value })} placeholder="AABCT1234A" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>GSTIN</label>
                <input className={inputCls} value={entity.gstin} onChange={(e) => setEntity({ ...entity, gstin: e.target.value })} placeholder="27AABCT1234A1Z5" />
              </div>
              <div>
                <label className={labelCls}>Sector *</label>
                <select className={inputCls} value={entity.sector} onChange={(e) => setEntity({ ...entity, sector: e.target.value })}>
                  <option value="">Select sector</option>
                  {SECTORS.map((s) => <option key={s} value={s.toLowerCase()}>{s}</option>)}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={labelCls}>Turnover (₹Cr)</label>
                <input type="number" className={inputCls} value={entity.annual_turnover_cr} onChange={(e) => setEntity({ ...entity, annual_turnover_cr: e.target.value })} placeholder="100" />
              </div>
              <div>
                <label className={labelCls}>Employees</label>
                <input type="number" className={inputCls} value={entity.employee_count} onChange={(e) => setEntity({ ...entity, employee_count: e.target.value })} placeholder="500" />
              </div>
              <div>
                <label className={labelCls}>Inc. Year</label>
                <input type="number" className={inputCls} value={entity.year_of_incorporation} onChange={(e) => setEntity({ ...entity, year_of_incorporation: e.target.value })} placeholder="2005" />
              </div>
            </div>
            <div>
              <label className={labelCls}>Registered Address</label>
              <input className={inputCls} value={entity.registered_address} onChange={(e) => setEntity({ ...entity, registered_address: e.target.value })} placeholder="Mumbai, Maharashtra" />
            </div>
            <button onClick={() => setStep(2)} disabled={!canAdvance1} className="w-full mt-2 h-[44px] bg-ob-text text-ob-bg text-[13px] font-bold rounded-[6px] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity">
              Continue to Loan Details →
            </button>
          </div>
        )}

        {/* Step 2: Loan */}
        {step === 2 && (
          <div className="space-y-4">
            <h1 className="font-display text-[24px] text-ob-text">Loan Application</h1>
            <p className="text-[12px] text-ob-muted">Specify the credit facility being requested.</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Loan Type *</label>
                <select className={inputCls} value={loan.loan_type} onChange={(e) => setLoan({ ...loan, loan_type: e.target.value })}>
                  <option value="">Select type</option>
                  {LOAN_TYPES.map((t) => <option key={t} value={t.toLowerCase().replace(/ /g, '_')}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>Amount (₹Cr) *</label>
                <input type="number" step="0.01" className={inputCls} value={loan.loan_amount_cr} onChange={(e) => setLoan({ ...loan, loan_amount_cr: e.target.value })} placeholder="50.00" />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className={labelCls}>Tenure (months) *</label>
                <input type="number" className={inputCls} value={loan.tenure_months} onChange={(e) => setLoan({ ...loan, tenure_months: e.target.value })} placeholder="36" />
              </div>
              <div>
                <label className={labelCls}>Proposed Rate %</label>
                <input type="number" step="0.01" className={inputCls} value={loan.proposed_rate_pct} onChange={(e) => setLoan({ ...loan, proposed_rate_pct: e.target.value })} placeholder="10.5" />
              </div>
              <div>
                <label className={labelCls}>Repayment</label>
                <select className={inputCls} value={loan.repayment_mode} onChange={(e) => setLoan({ ...loan, repayment_mode: e.target.value })}>
                  <option value="">Select</option>
                  {REPAYMENT_MODES.map((m) => <option key={m} value={m.toLowerCase()}>{m}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className={labelCls}>Purpose</label>
              <input className={inputCls} value={loan.purpose} onChange={(e) => setLoan({ ...loan, purpose: e.target.value })} placeholder="Working capital expansion, equipment purchase..." />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelCls}>Collateral Type</label>
                <input className={inputCls} value={loan.collateral_type} onChange={(e) => setLoan({ ...loan, collateral_type: e.target.value })} placeholder="Property / Inventory" />
              </div>
              <div>
                <label className={labelCls}>Collateral Value (₹Cr)</label>
                <input type="number" step="0.01" className={inputCls} value={loan.collateral_value_cr} onChange={(e) => setLoan({ ...loan, collateral_value_cr: e.target.value })} placeholder="75.00" />
              </div>
            </div>
            <div className="flex gap-3 mt-2">
              <button onClick={() => setStep(1)} className="flex-1 h-[44px] bg-ob-glass2 border border-ob-edge text-ob-text text-[13px] font-bold rounded-[6px] hover:bg-ob-glass transition-all">
                ← Back
              </button>
              <button onClick={() => setStep(3)} disabled={!canAdvance2} className="flex-[2] h-[44px] bg-ob-text text-ob-bg text-[13px] font-bold rounded-[6px] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity">
                Review →
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Review */}
        {step === 3 && (
          <div className="space-y-4">
            <h1 className="font-display text-[24px] text-ob-text">Review & Submit</h1>
            <p className="text-[12px] text-ob-muted">Confirm details before proceeding to document upload.</p>

            <div className="bg-ob-glass2 border border-ob-edge rounded-[8px] p-4 space-y-2 text-[12px]">
              <p className="font-mono text-[9px] text-ob-dim uppercase tracking-[0.12em]">Entity</p>
              <p className="text-ob-text font-medium">{entity.name}</p>
              <div className="flex flex-wrap gap-x-5 gap-y-1 text-ob-muted">
                {entity.cin && <span>CIN: <span className="text-ob-text font-mono">{entity.cin}</span></span>}
                {entity.sector && <span>Sector: <span className="text-ob-text">{entity.sector}</span></span>}
                {entity.annual_turnover_cr && <span>Turnover: <span className="text-ob-text font-mono">₹{entity.annual_turnover_cr} Cr</span></span>}
                {entity.year_of_incorporation && <span>Inc: <span className="text-ob-text font-mono">{entity.year_of_incorporation}</span></span>}
              </div>
            </div>

            <div className="bg-ob-glass2 border border-ob-edge rounded-[8px] p-4 space-y-2 text-[12px]">
              <p className="font-mono text-[9px] text-ob-dim uppercase tracking-[0.12em]">Loan</p>
              <div className="flex flex-wrap gap-x-5 gap-y-1 text-ob-muted">
                <span>Type: <span className="text-ob-text">{loan.loan_type}</span></span>
                <span>Amount: <span className="text-ob-text font-mono">₹{loan.loan_amount_cr} Cr</span></span>
                <span>Tenure: <span className="text-ob-text font-mono">{loan.tenure_months} mo</span></span>
                {loan.proposed_rate_pct && <span>Rate: <span className="text-ob-text font-mono">{loan.proposed_rate_pct}%</span></span>}
                {loan.repayment_mode && <span>Repayment: <span className="text-ob-text">{loan.repayment_mode}</span></span>}
              </div>
              {loan.purpose && <p className="text-ob-muted">Purpose: <span className="text-ob-text">{loan.purpose}</span></p>}
              {loan.collateral_type && <p className="text-ob-muted">Collateral: <span className="text-ob-text">{loan.collateral_type} — ₹{loan.collateral_value_cr || 0} Cr</span></p>}
            </div>

            {error && <p className="text-[12px] text-red-400 bg-red-400/10 border border-red-400/20 rounded-[6px] px-3 py-2">{error}</p>}

            <div className="flex gap-3 mt-2">
              <button onClick={() => setStep(2)} disabled={submitting} className="flex-1 h-[44px] bg-ob-glass2 border border-ob-edge text-ob-text text-[13px] font-bold rounded-[6px] hover:bg-ob-glass transition-all disabled:opacity-40">
                ← Back
              </button>
              <button onClick={handleSubmit} disabled={submitting} className="flex-[2] h-[44px] bg-ob-text text-ob-bg text-[13px] font-bold rounded-[6px] hover:opacity-90 disabled:opacity-60 transition-opacity">
                {submitting ? 'Creating…' : 'Create & Upload Documents →'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
