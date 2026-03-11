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
    <div className="bg-ob-bg py-12 px-4 md:px-6">
      <div className="max-w-[720px] mx-auto space-y-5">
        {/* Back button (only before pipeline starts) */}
        {!pipelineStarted && !complete && (
          <button onClick={() => router.push('/app/notes')} className="text-[13px] text-ob-muted hover:text-ob-text transition-colors">
            ← Back to Notes
          </button>
        )}

        <div>
          <h1 className="font-display text-[28px] font-normal text-ob-text">Processing Assessment</h1>
          <p className="text-[12px] font-mono text-ob-muted mt-1">
            {companyName || 'Not selected'} · {new Date().toLocaleString()}
          </p>
        </div>

        <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
          <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-4">Pipeline Stages</p>
          <div className="space-y-0">
            {FLOW_STEPS.map((step, idx) => {
              const isLast = idx === FLOW_STEPS.length - 1;
              return (
                <div key={step.title} className="flex gap-3">
                  <div className="flex flex-col items-center">
                    <div className="w-3 h-3 rounded-full border-2 border-ob-edge bg-ob-surface flex-shrink-0 mt-0.5" />
                    {!isLast && <div className="w-px flex-1 bg-ob-edge" />}
                  </div>
                  <div className="pb-4">
                    <p className="text-[13px] font-medium text-ob-text">{step.title}</p>
                    <p className="text-[11px] text-ob-muted mt-0.5">{step.subtitle}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
          <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Live Progress</p>
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
            <div className="bg-ob-warn-bg border border-ob-warn-edge rounded-[10px] p-4">
              <p className="text-ob-warn text-[13px]">No company found. Please start from the Upload page.</p>
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-3">
          {hitlReached && !complete && (
            <button
              onClick={() => router.push('/app/notes')}
              className="py-[12px] px-[24px] bg-ob-glass2 border border-ob-edge text-ob-text font-body font-medium rounded-[6px] text-[13px] transition-all hover:bg-ob-glass hover:border-ob-edge2"
            >
              Add credit officer notes
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
