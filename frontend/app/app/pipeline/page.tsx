'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAnalysisStore } from '@/store/analysisStore';
import AgentProgressLog from '@/components/AgentProgressLog';

const FLOW_STEPS = [
  { title: 'Document Understanding', subtitle: 'Reading uploaded files and extracting key data' },
  { title: 'Financial Consistency', subtitle: 'GST, banking, and tax return cross-checks' },
  { title: 'Public & Regulatory Research', subtitle: 'News, litigation, MCA, and compliance scan' },
  { title: 'Risk Scoring', subtitle: 'Policy rules + model-based risk estimation' },
  { title: 'CAM Draft Generation', subtitle: 'Compiles decision rationale and recommendation' },
];

export default function PipelinePage() {
  const [hitlReached, setHitlReached] = useState(false);
  const [complete, setComplete] = useState(false);
  const [pipelineStarted, setPipelineStarted] = useState(false);
  const { companyId, companyName, setPipelineStatus, advanceStep } = useAnalysisStore();
  const router = useRouter();

  return (
    <div className="bg-ic-page py-12 px-4 md:px-6">
      <div className="max-w-[720px] mx-auto space-y-5">
        {/* Back button (only before pipeline starts) */}
        {!pipelineStarted && !complete && (
          <button onClick={() => router.push('/app/notes')} className="text-[13px] text-ic-muted hover:text-ic-text transition-colors">
            ← Back to Notes
          </button>
        )}

        <div>
          <h1 className="font-display text-[28px] font-normal text-ic-text">Processing Assessment</h1>
          <p className="text-[12px] font-mono text-ic-muted mt-1">
            {companyName || 'Not selected'} · {new Date().toLocaleString()}
          </p>
        </div>

        <div className="bg-ic-surface border border-ic-border rounded-[10px] p-5">
          <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ic-muted mb-4">Pipeline Stages</p>
          <div className="space-y-0">
            {FLOW_STEPS.map((step, idx) => {
              const isLast = idx === FLOW_STEPS.length - 1;
              return (
                <div key={step.title} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className="w-3 h-3 rounded-full border-2 border-ic-border bg-ic-surface flex-shrink-0 mt-0.5" />
                    {!isLast && <div className="w-px flex-1 bg-ic-border" />}
                  </div>
                  <div className="pb-4">
                    <p className="text-[13px] font-medium text-ic-text">{step.title}</p>
                    <p className="text-[11px] text-ic-muted mt-0.5">{step.subtitle}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-ic-surface border border-ic-border rounded-[10px] p-5">
          <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ic-muted mb-2.5">Live Progress</p>
          {companyId ? (
            <AgentProgressLog
              companyId={companyId}
              onHitlReached={() => {
                setHitlReached(true);
                setPipelineStarted(true);
                setPipelineStatus('hitl');
              }}
              onComplete={() => {
                setComplete(true);
                setPipelineStarted(true);
                setPipelineStatus('complete');
                advanceStep(); // step 2 → 3
                router.push('/app/score');
              }}
            />
          ) : (
            <div className="bg-[#fdf0e8] border border-[#f3d5bc] rounded-[10px] p-4">
              <p className="text-ic-warning text-[13px]">No company found. Please start from the Upload page.</p>
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-3">
          {hitlReached && !complete && (
            <button
              onClick={() => router.push('/app/notes')}
              className="py-2.5 px-5 bg-ic-tan text-ic-text font-medium rounded-[10px] text-[13px] transition-opacity hover:opacity-90"
            >
              Add credit officer notes
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
