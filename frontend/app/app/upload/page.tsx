'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import UploadZone from '@/components/UploadZone';
import { useAnalysisStore } from '@/store/analysisStore';
import {
  createCompanyV1,
  getIntegrationHealthV1,
  previewDueDiligenceV1,
  submitDueDiligenceV1,
  triggerAnalysisV1,
  uploadDocumentsV1,
} from '@/lib/api';

const UPLOAD_STAGES = [
  'Documents received',
  'Reading files',
  'Tax and bank checks',
];

const SUPPORTED_FORMATS = [
  { type: 'PDF', desc: 'Annual reports, audit reports' },
  { type: 'CSV / XLS', desc: 'Bank statements, financial data' },
  { type: 'XML / JSON', desc: 'GST filings, ITR returns' },
  { type: 'DOCX', desc: 'Word-format financials' },
  { type: 'JPEG / PNG', desc: 'Scanned documents' },
];

export default function UploadPage() {
  const router = useRouter();
  const { companyName: storedName, setCompany, setUploadedFileNames, advanceStep } = useAnalysisStore();

  const [files, setFiles] = useState<File[]>([]);
  const [companyName, setCompanyName] = useState('');
  const [sector, setSector] = useState('agri_processing');
  const [loanAmount, setLoanAmount] = useState(50);
  const [loanPurpose, setLoanPurpose] = useState('working_capital');
  const [loading, setLoading] = useState(false);
  const [activeStage, setActiveStage] = useState<number>(-1);
  const [error, setError] = useState('');
  const [optionalOpen, setOptionalOpen] = useState(false);
  const [integrationHealth, setIntegrationHealth] = useState<any | null>(null);
  const [integrationLoading, setIntegrationLoading] = useState(false);
  const [integrationError, setIntegrationError] = useState('');
  const [duePreview, setDuePreview] = useState<any | null>(null);
  const [duePreviewLoading, setDuePreviewLoading] = useState(false);

  const [financeOfficerName, setFinanceOfficerName] = useState('');
  const [financeOfficerRole, setFinanceOfficerRole] = useState('Finance Officer');
  const [financeOfficerEmail, setFinanceOfficerEmail] = useState('');
  const [financeOfficerPhone, setFinanceOfficerPhone] = useState('');
  const [capacityPct, setCapacityPct] = useState(70);
  const [inventoryLevel, setInventoryLevel] = useState('ADEQUATE');
  const [managementCooperation, setManagementCooperation] = useState('COOPERATIVE');
  const [businessHighlights, setBusinessHighlights] = useState('');
  const [keyRisksDisclosed, setKeyRisksDisclosed] = useState('');
  const [majorCustomers, setMajorCustomers] = useState('');
  const [contingentLiabilities, setContingentLiabilities] = useState('');
  const [plannedCapex, setPlannedCapex] = useState('');

  useEffect(() => {
    setCompanyName(storedName || 'Vardhman Agri Processing Pvt. Ltd.');
  }, [storedName]);

  const checkIntegrations = async (liveChecks: boolean) => {
    setIntegrationLoading(true);
    setIntegrationError('');
    try {
      const res = await getIntegrationHealthV1(liveChecks);
      setIntegrationHealth(res.data);
    } catch (err: any) {
      setIntegrationError(err?.response?.data?.detail || err?.message || 'Unable to fetch integration health');
    } finally {
      setIntegrationLoading(false);
    }
  };

  useEffect(() => {
    void checkIntegrations(false);
  }, []);

  const hasOptionalInputs = Boolean(
    financeOfficerName.trim() || financeOfficerEmail.trim() || financeOfficerPhone.trim() ||
    businessHighlights.trim() || keyRisksDisclosed.trim() || majorCustomers.trim() ||
    contingentLiabilities.trim() || plannedCapex.trim() || capacityPct !== 70 ||
    inventoryLevel !== 'ADEQUATE' || managementCooperation !== 'COOPERATIVE'
  );

  const buildDueDiligenceNotes = () => {
    return [
      `Borrower finance officer name: ${financeOfficerName || 'Not provided'}`,
      `Role: ${financeOfficerRole || 'Not provided'}`,
      `Email: ${financeOfficerEmail || 'Not provided'}`,
      `Phone: ${financeOfficerPhone || 'Not provided'}`,
      `Business highlights: ${businessHighlights || 'Not provided'}`,
      `Key risks disclosed by borrower: ${keyRisksDisclosed || 'Not provided'}`,
      `Major customers and concentration: ${majorCustomers || 'Not provided'}`,
      `Contingent liabilities: ${contingentLiabilities || 'Not provided'}`,
      `Planned capex / expansion: ${plannedCapex || 'Not provided'}`,
    ].join('\n');
  };

  useEffect(() => {
    let cancelled = false;
    if (!hasOptionalInputs) { setDuePreview(null); return; }
    const timer = setTimeout(async () => {
      setDuePreviewLoading(true);
      try {
        const response = await previewDueDiligenceV1(companyName || 'Borrower', buildDueDiligenceNotes());
        if (!cancelled) setDuePreview(response.data);
      } catch { if (!cancelled) setDuePreview(null); }
      finally { if (!cancelled) setDuePreviewLoading(false); }
    }, 450);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [
    hasOptionalInputs, companyName, financeOfficerName, financeOfficerRole,
    financeOfficerEmail, financeOfficerPhone, capacityPct, inventoryLevel,
    managementCooperation, businessHighlights, keyRisksDisclosed,
    majorCustomers, contingentLiabilities, plannedCapex,
  ]);

  const startAnalysis = async () => {
    if (!files.length || !companyName.trim()) return;
    setLoading(true);
    setError('');
    let failedStep = 'starting analysis';
    try {
      setActiveStage(0);
      failedStep = 'creating company profile';
      const companyRes = await createCompanyV1({
        name: companyName, sector, loan_amount_requested: loanAmount,
        loan_tenor_months: 36, loan_purpose: loanPurpose,
      });
      const companyId = companyRes.data.company_id;
      setCompany(companyId, companyName);
      setUploadedFileNames(files.map((f) => f.name));

      if (hasOptionalInputs) {
        failedStep = 'submitting borrower context';
        await submitDueDiligenceV1(companyId, {
          capacity_utilization_percent: capacityPct, inventory_levels: inventoryLevel,
          management_cooperation: managementCooperation, free_text_notes: buildDueDiligenceNotes(),
          key_management_persons: financeOfficerName.trim()
            ? [{ name: financeOfficerName.trim(), role: financeOfficerRole.trim() || 'Finance Officer', notes: 'Borrower representative input captured at application time.' }]
            : [],
          borrower_finance_officer_name: financeOfficerName || undefined,
          borrower_finance_officer_role: financeOfficerRole || undefined,
          borrower_finance_officer_email: financeOfficerEmail || undefined,
          borrower_finance_officer_phone: financeOfficerPhone || undefined,
          borrower_business_highlights: businessHighlights || undefined,
          borrower_major_customers: majorCustomers || undefined,
          borrower_contingent_liabilities: contingentLiabilities || undefined,
          borrower_planned_capex: plannedCapex || undefined,
          borrower_disclosed_risks: keyRisksDisclosed || undefined,
        });
      }

      setActiveStage(1);
      failedStep = 'uploading documents';
      await uploadDocumentsV1(companyId, files);
      setActiveStage(2);
      failedStep = 'triggering pipeline';
      await triggerAnalysisV1(companyId);
      setActiveStage(3);
      await new Promise((resolve) => setTimeout(resolve, 250));
      advanceStep(); // step 0 → 1
      router.push('/app/notes');
    } catch (err: any) {
      const rawMessage = String(err?.response?.data?.detail || err?.message || 'Upload failed');
      setError(rawMessage.toLowerCase().includes('network error')
        ? `Network error while ${failedStep}. Backend API is not reachable. Start backend and retry.`
        : rawMessage);
    } finally {
      setLoading(false);
    }
  };

  const labelClass = 'font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim';
  const inputClass = 'mt-[8px] w-full rounded-[6px] bg-ob-glass2 border border-ob-edge px-4 py-2 text-[13px] text-ob-text focus:outline-none focus:ring-1 focus:ring-ob-text/50 transition-all font-body font-light';

  return (
    <div className="bg-ob-bg py-10 px-4 md:px-8">
      <div className="max-w-[1100px] mx-auto flex flex-col lg:flex-row gap-5">
        {/* Left column — 60% */}
        <div className="flex-[3] space-y-5">
          <div>
            <h1 className="font-display text-[26px] font-normal text-ob-text">Upload Documents</h1>
            <p className="text-[14px] text-ob-muted mt-1">Add company details, upload documents, and start CAM preparation.</p>
          </div>

          {/* Basic details card */}
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className={`${labelClass} mb-2.5`}>Application Details</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <label className={`md:col-span-2 ${labelClass}`}>Company name<input value={companyName} onChange={(e) => setCompanyName(e.target.value)} placeholder="e.g. Vizag Steel Works Pvt Ltd" className={inputClass} /></label>
              <label className={labelClass}>Loan amount (INR Cr)<input type="number" value={loanAmount} onChange={(e) => setLoanAmount(Number(e.target.value))} className={inputClass} /></label>
              <label className={`md:col-span-2 ${labelClass}`}>Sector
                <select value={sector} onChange={(e) => setSector(e.target.value)} className={`${inputClass} bg-ob-glass2`}>
                  {['agri_processing', 'manufacturing', 'nbfc', 'real_estate', 'textiles', 'it_services'].map((s) => (<option key={s} value={s} className="bg-ob-surface text-ob-text">{s.replace('_', ' ').toUpperCase()}</option>))}
                </select>
              </label>
              <label className={labelClass}>Purpose
                <select value={loanPurpose} onChange={(e) => setLoanPurpose(e.target.value)} className={`${inputClass} bg-ob-glass2`}>
                  <option value="working_capital" className="bg-ob-surface text-ob-text">Working Capital</option><option value="term_loan" className="bg-ob-surface text-ob-text">Term Loan</option><option value="capex" className="bg-ob-surface text-ob-text">Capex</option><option value="refinance" className="bg-ob-surface text-ob-text">Refinance</option>
                </select>
              </label>
            </div>
          </div>

          {/* Upload dropzone */}
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className={`${labelClass} mb-2.5`}>Documents</p>
            <UploadZone onFilesReady={setFiles} />
          </div>

          {/* Optional borrower input */}
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px] space-y-4">
            <button type="button" onClick={() => setOptionalOpen((prev) => !prev)} className="w-full flex items-center justify-between text-left bg-transparent border-none cursor-pointer">
              <span className="text-[14px] font-medium text-ob-text">Optional borrower input (Finance Officer)</span>
              <span className="text-[12px] text-ob-muted">{optionalOpen ? 'Hide' : 'Add details'}</span>
            </button>
            {optionalOpen && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className={labelClass}>Finance officer name<input value={financeOfficerName} onChange={(e) => setFinanceOfficerName(e.target.value)} className={inputClass} /></label>
                <label className={labelClass}>Role<input value={financeOfficerRole} onChange={(e) => setFinanceOfficerRole(e.target.value)} className={inputClass} /></label>
                <label className={labelClass}>Email<input type="email" value={financeOfficerEmail} onChange={(e) => setFinanceOfficerEmail(e.target.value)} className={inputClass} /></label>
                <label className={labelClass}>Phone<input value={financeOfficerPhone} onChange={(e) => setFinanceOfficerPhone(e.target.value)} className={inputClass} /></label>
                <label className={labelClass}>Capacity utilization ({capacityPct}%)<input type="range" min={0} max={100} value={capacityPct} onChange={(e) => setCapacityPct(Number(e.target.value))} className="mt-2 w-full" /></label>
                <label className={labelClass}>Inventory situation<select value={inventoryLevel} onChange={(e) => setInventoryLevel(e.target.value)} className={`${inputClass} bg-ob-glass2`}><option value="ADEQUATE" className="bg-ob-surface text-ob-text">Adequate</option><option value="LOW" className="bg-ob-surface text-ob-text">Low</option><option value="EXCESS" className="bg-ob-surface text-ob-text">Excess</option><option value="SUSPICIOUS" className="bg-ob-surface text-ob-text">Needs review</option></select></label>
                <label className={labelClass}>Management cooperation<select value={managementCooperation} onChange={(e) => setManagementCooperation(e.target.value)} className={`${inputClass} bg-ob-glass2`}><option value="COOPERATIVE" className="bg-ob-surface text-ob-text">Cooperative</option><option value="EVASIVE" className="bg-ob-surface text-ob-text">Evasive</option><option value="REFUSED" className="bg-ob-surface text-ob-text">Refused key clarifications</option></select></label>
                <label className={labelClass}>Major customers<input value={majorCustomers} onChange={(e) => setMajorCustomers(e.target.value)} placeholder="Top buyers and concentration" className={inputClass} /></label>
                <label className={`md:col-span-2 ${labelClass}`}>Business highlights<textarea value={businessHighlights} onChange={(e) => setBusinessHighlights(e.target.value)} rows={3} placeholder="Orders, seasonal trends, utilization" className={`${inputClass} min-h-[100px]`} /></label>
                <label className={`md:col-span-2 ${labelClass}`}>Risks disclosed by borrower<textarea value={keyRisksDisclosed} onChange={(e) => setKeyRisksDisclosed(e.target.value)} rows={2} placeholder="Any expected disruptions" className={`${inputClass} min-h-[80px]`} /></label>
                <label className={labelClass}>Contingent liabilities<input value={contingentLiabilities} onChange={(e) => setContingentLiabilities(e.target.value)} className={inputClass} /></label>
                <label className={labelClass}>Planned capex<input value={plannedCapex} onChange={(e) => setPlannedCapex(e.target.value)} className={inputClass} /></label>
              </div>
            )}
            <p className="text-[12px] text-ob-muted">These fields are optional. If provided, they are used as borrower clarifications in risk scoring and CAM.</p>
            {hasOptionalInputs && (
              <div className="bg-ob-glass2 border border-ob-edge rounded-[10px] p-4">
                <p className="text-[13px] font-medium text-ob-text">Estimated borrower-input score adjustment</p>
                <p className="text-[12px] text-ob-muted mt-1">{duePreviewLoading ? 'Calculating expected impact...' : `${Number(duePreview?.score_adjustment || 0) >= 0 ? '+' : ''}${Number(duePreview?.score_adjustment || 0).toFixed(1)} raw adjustment`}</p>
                {!!duePreview?.risk_factors?.length && <p className="text-[11px] text-ob-warn mt-2">Risk cues: {duePreview.risk_factors.slice(0, 4).join(', ')}</p>}
                {!!duePreview?.positive_factors?.length && <p className="text-[11px] text-ob-ok mt-1">Positive cues: {duePreview.positive_factors.slice(0, 4).join(', ')}</p>}
              </div>
            )}
          </div>

          {/* Upload progress */}
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className={`${labelClass} mb-2.5`}>Upload Progress</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {UPLOAD_STAGES.map((stage, idx) => {
                const completed = idx < activeStage;
                const active = idx === activeStage && loading;
                return (
                  <div key={stage} className={`rounded-[6px] px-3 py-2 text-[12px] font-body border ${completed ? 'bg-ob-glass2 border-ob-text/30 text-[rgba(180,240,180,0.7)]' : active ? 'bg-ob-glass2 border-ob-text/50 text-ob-text animate-pulse' : 'bg-transparent border-ob-edge text-ob-muted'}`}>
                    {completed ? '✓ ' : active ? '◌ ' : '○ '} {stage}
                  </div>
                );
              })}
            </div>
          </div>

          {error && (<div className="bg-ob-warn-bg border border-ob-warn-edge rounded-[10px] p-4"><p className="text-ob-warn text-[13px]">{error}</p></div>)}

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              onClick={startAnalysis}
              disabled={loading || files.length === 0}
              className="flex-1 py-[12px] rounded-[6px] bg-ob-text text-ob-bg font-body font-bold text-[13px] tracking-[0.04em] transition-opacity hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {loading ? 'Starting your CAM analysis...' : `Continue to Analyst Notes → (${files.length} files)`}
            </button>
          </div>
        </div>

        {/* Right column — 40% */}
        <div className="flex-[2] space-y-5">
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className={`${labelClass} mb-2.5`}>What to Upload</p>
            <div className="space-y-2">
              {['Annual Report / Balance Sheet', 'Bank Statements (12 months)', 'GST Returns (GSTR-3B)', 'IT Returns (ITR)', 'Audit Report'].map((item) => (
                <div key={item} className="flex items-center gap-2 py-1"><span className="w-4 h-4 rounded-full border-2 border-ob-edge flex-shrink-0" /><span className="text-[13px] text-ob-text">{item}</span></div>
              ))}
            </div>
          </div>
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className={`${labelClass} mb-2.5`}>Supported Formats</p>
            <div className="space-y-1.5">
              {SUPPORTED_FORMATS.map((f) => (<div key={f.type} className="flex justify-between text-[12px]"><span className="font-mono font-medium text-ob-text">{f.type}</span><span className="text-ob-muted">{f.desc}</span></div>))}
            </div>
          </div>
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <div className="flex items-center justify-between gap-3 mb-2.5">
              <p className={labelClass}>Tool Connectivity</p>
              <button type="button" onClick={() => checkIntegrations(true)} className="px-3 py-1 rounded-md bg-ob-text text-ob-bg text-[11px] font-bold disabled:opacity-40 transition-colors hover:bg-ob-cream" disabled={integrationLoading}>{integrationLoading ? 'Checking...' : 'Run live check'}</button>
            </div>
            {integrationError && (<div className="bg-ob-warn-bg border border-ob-warn-edge rounded-md p-2 mb-2"><p className="text-ob-warn text-[11px]">{integrationError}</p></div>)}
            {integrationHealth?.integrations && (
              <div className="space-y-2">
                {Object.entries(integrationHealth.integrations).map(([tool, info]: [string, any]) => (
                  <div key={tool} className="rounded-md border border-ob-edge bg-ob-surface2 p-2.5">
                    <p className="text-[12px] font-medium text-ob-text capitalize">{tool.replace('_', ' ')}</p>
                    <p className="text-[11px] text-ob-muted">{info.configured ? 'Configured' : 'Not configured'} · {info.ok ? 'OK' : 'Issue'}</p>
                    {info.error && <p className="text-[11px] text-ob-warn mt-0.5">{String(info.error)}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
