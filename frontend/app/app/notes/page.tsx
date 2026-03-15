'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAnalysisStore } from '@/store/analysisStore';
import { previewDueDiligenceV1, submitDueDiligenceV1, triggerAnalysisV1 } from '@/lib/api';

function useDebounce<T>(value: T, delay = 600): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

export default function DueDiligencePage() {
  const router = useRouter();
  const { companyId, companyName, advanceStep } = useAnalysisStore();

  const [factoryVisitDate, setFactoryVisitDate] = useState('');
  const [capacity, setCapacity] = useState(68);
  const [factoryCondition, setFactoryCondition] = useState('GOOD');
  const [inventoryLevels, setInventoryLevels] = useState('ADEQUATE');
  const [managementCooperation, setManagementCooperation] = useState('COOPERATIVE');
  const [notes, setNotes] = useState('');
  const [interviewRating, setInterviewRating] = useState(3);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<any>(null);
  const [error, setError] = useState('');

  const debouncedNotes = useDebounce(notes, 650);
  const charCount = notes.length;

  const sections = [
    { label: 'Factory visit date', filled: !!factoryVisitDate },
    { label: 'Assessment ratings', filled: interviewRating > 0 },
    { label: 'Capacity utilization', filled: capacity !== 68 },
    { label: 'Condition & inventory', filled: true },
    { label: 'Free-text notes', filled: notes.trim().length > 0 },
  ];

  useEffect(() => {
    if (!debouncedNotes.trim()) return;
    previewDueDiligenceV1(companyName || 'Unknown', debouncedNotes)
      .then((res) => setPreview(res.data))
      .catch(() => setPreview(null));
  }, [companyName, debouncedNotes]);

  const handleSubmit = async () => {
    if (!notes.trim() || !companyId) return;
    setLoading(true);
    setError('');
    try {
      await submitDueDiligenceV1(companyId, {
        factory_visit_date: factoryVisitDate || undefined,
        capacity_utilization_percent: capacity,
        factory_condition: factoryCondition,
        inventory_levels: inventoryLevels,
        management_cooperation: managementCooperation,
        free_text_notes: notes,
        management_interview_rating: interviewRating,
        key_management_persons: [],
      });
      await triggerAnalysisV1(companyId);
      advanceStep(); // step 1 → 2
      router.push('/app/pipeline');
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Submission failed');
    } finally {
      setLoading(false);
    }
  };

  const labelClass = 'font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim';
  const inputClass = 'mt-[8px] w-full rounded-[6px] bg-ob-glass2 border border-ob-edge px-3 py-2 text-[13px] text-ob-text focus:outline-none focus:ring-1 focus:ring-ob-text/50 transition-all font-body font-light';

  return (
    <div className="bg-ob-bg py-10 px-4 md:px-8">
      <div className="max-w-[1100px] mx-auto flex flex-col lg:flex-row gap-5">
        {/* Left column — 65% */}
        <div className="flex-[65] space-y-5">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-display text-[26px] font-normal text-ob-text">Due Diligence Portal</h1>
              <span className="text-[11px] font-mono text-ob-muted bg-ob-surface2 px-2 py-0.5 rounded">Step 2 of 4</span>
            </div>
            <p className="text-[14px] text-ob-muted mt-1">
              Credit Officer input for <span className="font-medium text-ob-text">{companyName || 'Unknown Company'}</span>
            </p>
          </div>

          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <h2 className="font-display text-[18px] text-ob-text mb-4">Business Overview</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className={labelClass}>Factory Visit Date<input type="date" value={factoryVisitDate} onChange={(e) => setFactoryVisitDate(e.target.value)} className={inputClass} /></label>
              <label className={labelClass}>Management Interview Rating ({interviewRating}/5)<input type="range" min={1} max={5} value={interviewRating} onChange={(e) => setInterviewRating(Number(e.target.value))} className="mt-2 w-full" /></label>
            </div>
          </div>

          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <h2 className="font-display text-[18px] text-ob-text mb-4">Management & Governance</h2>
            <div className="mb-4">
              <label className={`block ${labelClass} mb-1`}>Capacity Utilization ({capacity}%)</label>
              <input type="range" min={0} max={100} value={capacity} onChange={(e) => setCapacity(Number(e.target.value))} className="w-full" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <label className={labelClass}>Factory Condition<select value={factoryCondition} onChange={(e) => setFactoryCondition(e.target.value)} className={`${inputClass} bg-ob-glass2`}>{['EXCELLENT', 'GOOD', 'FAIR', 'POOR'].map((x) => (<option key={x} value={x} className="bg-ob-surface text-ob-text">{x}</option>))}</select></label>
              <label className={labelClass}>Inventory Levels<select value={inventoryLevels} onChange={(e) => setInventoryLevels(e.target.value)} className={`${inputClass} bg-ob-glass2`}>{['ADEQUATE', 'LOW', 'EXCESS', 'SUSPICIOUS'].map((x) => (<option key={x} value={x} className="bg-ob-surface text-ob-text">{x}</option>))}</select></label>
              <label className={labelClass}>Management Cooperation<select value={managementCooperation} onChange={(e) => setManagementCooperation(e.target.value)} className={`${inputClass} bg-ob-glass2`}>{['COOPERATIVE', 'EVASIVE', 'REFUSED'].map((x) => (<option key={x} value={x} className="bg-ob-surface text-ob-text">{x}</option>))}</select></label>
            </div>
          </div>

          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <h2 className="font-display text-[18px] text-ob-text mb-4">Analyst Notes</h2>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={8} placeholder="Mention production, order-book, utilization, inventory quality, management behavior..." className={`${inputClass} min-h-[100px]`} />
            <p className="text-[11px] text-ob-muted mt-1 font-mono">{charCount} characters</p>
          </div>

          {error && (<div className="bg-ob-warn-bg border border-ob-warn-edge rounded-[10px] p-3"><p className="text-ob-warn text-[13px]">{error}</p></div>)}

          {/* Footer row: Back + Submit */}
          <div className="flex items-center justify-between">
            <button onClick={() => router.push('/app/upload')} className="text-[13px] text-ob-muted hover:text-ob-text transition-colors">← Back to Upload</button>
            <button onClick={handleSubmit} disabled={loading || !notes.trim()} className="py-[12px] px-8 rounded-[6px] bg-ob-text text-ob-bg text-[13px] font-body font-bold tracking-[0.04em] transition-opacity hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed">
              {loading ? 'Submitting...' : 'Run Analysis →'}
            </button>
          </div>
        </div>

        {/* Right column — 35%, sticky */}
        <div className="flex-[35] space-y-5 lg:sticky lg:top-[72px] lg:self-start">
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Completion</p>
            <div className="space-y-2">
              {sections.map((s) => (
                <div key={s.label} className="flex items-center gap-2 text-[13px]">
                  <span className={`w-4 h-4 rounded-full flex-shrink-0 ${s.filled ? 'bg-ob-text' : 'border-2 border-ob-edge'}`} />
                  <span className={s.filled ? 'text-ob-text' : 'text-ob-muted'}>{s.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Live AI Analysis</p>
            {!preview ? (
              <p className="text-ob-muted text-[13px]">Start typing notes to see extracted risk flags in real-time.</p>
            ) : (
              <div className="space-y-3 text-[13px]">
                <p className="text-ob-text">Sentiment: <span className="font-medium">{preview.sentiment}</span></p>
                <div><p className="font-medium text-ob-warn text-[12px]">Risk Factors</p><ul className="mt-1 space-y-1">{(preview.risk_factors || []).map((x: string, i: number) => (<li key={i} className="text-ob-warn text-[12px]">• {x}</li>))}</ul></div>
                <div><p className="font-medium text-ob-ok text-[12px]">Positive Factors</p><ul className="mt-1 space-y-1">{(preview.positive_factors || []).map((x: string, i: number) => (<li key={i} className="text-ob-ok text-[12px]">• {x}</li>))}</ul></div>
                <p className="text-ob-text">Suggested Adjustment: <span className="font-mono font-medium">{Number(preview.score_adjustment).toFixed(1)}</span></p>
              </div>
            )}
          </div>

          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Tips</p>
            <ul className="space-y-1.5 text-[12px] text-ob-muted">
              <li>• Mention production volume and capacity utilization trends</li>
              <li>• Note any regulatory or environmental concerns</li>
              <li>• Describe management responsiveness and transparency</li>
              <li>• Include order-book visibility if available</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
