'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAnalysisStore } from '@/store/analysisStore';

export default function StartPage() {
  const [companyName, setCompanyName] = useState('');
  const router = useRouter();
  const { setCompany, setPipelineStep } = useAnalysisStore();

  const handleSubmit = () => {
    if (!companyName.trim()) return;
    // Set session cookie for middleware gating
    document.cookie = 'ic_session=1; path=/; max-age=86400';
    setCompany('', companyName.trim());
    setPipelineStep(0);
    router.push('/app/upload');
  };

  return (
    <div className="min-h-screen bg-ic-page flex items-center justify-center px-4 pt-[60px]">
      <div className="bg-ic-surface border border-ic-border rounded-[14px] p-10 max-w-[480px] w-full shadow-sm">
        {/* Eyebrow */}
        <p className="font-mono text-[10px] text-ic-muted tracking-[0.12em] uppercase">
          Step 1 of 4
        </p>

        {/* Heading */}
        <h1 className="font-display text-[28px] font-normal text-ic-text mt-3">
          Who are you assessing?
        </h1>

        {/* Subtext */}
        <p className="text-[13px] text-ic-muted mt-2">
          Enter the company name to begin your credit assessment.
        </p>

        {/* Input */}
        <input
          type="text"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder="e.g. Vardhman Agri Processing Pvt. Ltd."
          className="w-full mt-6 h-12 px-4 bg-ic-surface border border-ic-border rounded-[8px] text-ic-text text-[14px] placeholder:text-ic-muted focus:outline-none focus:ring-2 focus:ring-ic-accent/30 focus:border-transparent"
        />

        {/* CTA */}
        <button
          onClick={handleSubmit}
          disabled={!companyName.trim()}
          className="w-full mt-4 h-12 bg-ic-accent text-white text-[14px] font-medium rounded-[8px] transition-opacity hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Begin Assessment →
        </button>
      </div>
    </div>
  );
}
