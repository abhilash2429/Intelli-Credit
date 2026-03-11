'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function HeroPage() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <div className="bg-ob-bg min-h-screen pt-[120px] pb-20 flex justify-center">
      {/* Container */}
      <div className="relative z-10 flex flex-col lg:flex-row items-start gap-[80px] px-[60px] max-w-[1440px] w-full">

        {/* LEFT */}
        <div className={`flex-1 pt-5 transition-all duration-1000 transform ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0'}`}>
          <div className="font-mono text-[10px] text-ob-muted tracking-[0.16em] uppercase mb-8">
            Corporate credit appraisal · AI-powered · Indian lending
          </div>

          <h1 className="font-display text-[clamp(46px,4.8vw,72px)] font-normal leading-[1.12] tracking-[-0.015em] text-ob-text mb-7">
            The credit appraisal<br />
            that writes <em className="italic opacity-60">itself.</em>
          </h1>

          <div className="w-[40px] h-[1px] bg-ob-edge2 mb-6 opacity-80" />

          <p className="text-[15px] font-light text-ob-muted leading-[1.85] max-w-[440px] mb-10">
            Upload a borrower&apos;s documents. Our pipeline ingests, researches, scores, and generates a complete Credit Appraisal Memo — in the time it takes to make a cup of tea. No manual steps. No waiting.
          </p>

          <div className="flex gap-[10px] mb-[56px]">
            <Link
              href="/app/start"
              className="bg-ob-text text-ob-bg font-body text-[13px] font-bold px-[32px] py-[13px] border-none rounded-[6px] tracking-[0.04em] transition-all duration-200 hover:bg-ob-cream no-underline"
            >
              Begin Assessment
            </Link>
            <Link
              href="#how-it-works"
              className="bg-transparent text-ob-muted font-body text-[13px] font-normal px-[24px] py-[12px] border border-ob-edge rounded-[6px] transition-all duration-200 hover:border-ob-edge2 hover:text-ob-text no-underline"
            >
              How it works →
            </Link>
          </div>

          <div className="flex flex-col gap-0 border-y border-ob-edge" id="how-it-works">
            {/* Step 01 */}
            <div className="flex gap-[20px] py-[18px] border-b border-ob-edge">
              <div className="font-mono text-[10px] text-ob-dim pt-[2px] shrink-0 w-[24px]">01</div>
              <div>
                <div className="font-display text-[15px] text-ob-text mb-1">Document Ingestion</div>
                <div className="text-[11px] font-normal text-ob-muted leading-[1.6]">
                  GST returns, bank statements, ITR, annual reports and scanned PDFs — parsed and cross-validated automatically.
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">GSTR-3B</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">Bank CSV</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">ITR JSON</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">OCR</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">PDF/DOCX</span>
                </div>
              </div>
            </div>

            {/* Step 02 */}
            <div className="flex gap-[20px] py-[18px] border-b border-ob-edge">
              <div className="font-mono text-[10px] text-ob-dim pt-[2px] shrink-0 w-[24px]">02</div>
              <div>
                <div className="font-display text-[15px] text-ob-text mb-1">Autonomous Web Research</div>
                <div className="text-[11px] font-normal text-ob-muted leading-[1.6]">
                  AI agents sweep MCA21, eCourts, news archives and promoter databases without a single manual search.
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">MCA21</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">eCourts</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">News</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">Promoter Intel</span>
                </div>
              </div>
            </div>

            {/* Step 03 */}
            <div className="flex gap-[20px] py-[18px] border-b border-ob-edge">
              <div className="font-mono text-[10px] text-ob-dim pt-[2px] shrink-0 w-[24px]">03</div>
              <div>
                <div className="font-display text-[15px] text-ob-text mb-1">Explainable ML Scoring</div>
                <div className="text-[11px] font-normal text-ob-muted leading-[1.6]">
                  XGBoost model calibrated to Indian lending data. Every factor explained via SHAP. Hard rejection rules enforced first.
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">XGBoost</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">SHAP</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">Five Cs</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">Risk Premium</span>
                </div>
              </div>
            </div>

            {/* Step 04 */}
            <div className="flex gap-[20px] py-[18px]">
              <div className="font-mono text-[10px] text-ob-dim pt-[2px] shrink-0 w-[24px]">04</div>
              <div>
                <div className="font-display text-[15px] text-ob-text mb-1">CAM Output + Export</div>
                <div className="text-[11px] font-normal text-ob-muted leading-[1.6]">
                  A 9-section Credit Appraisal Memo formatted to Indian banking standards. Download as Word or PDF instantly.
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">Word DOCX</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">PDF</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">9 Sections</span>
                  <span className="font-mono text-[9px] text-ob-dim px-[7px] py-[2px] border border-ob-edge rounded-[3px]">Chat</span>
                </div>
              </div>
            </div>

          </div>
        </div>

        {/* RIGHT — stacked cards */}
        <div className={`w-full lg:w-[360px] shrink-0 flex flex-col gap-[10px] pt-1 transition-all duration-1000 delay-300 transform ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0'}`}>
          {/* Score */}
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <div className="font-mono text-[9px] text-ob-dim tracking-[0.14em] uppercase mb-[14px]">
              Risk Score · Vardhman Agri Processing
            </div>
            <div className="font-display text-[58px] text-ob-text leading-[1] tracking-[-0.03em]">
              6.4<small className="text-[18px] text-ob-muted font-body font-light"> /10</small>
            </div>
            <div className="text-[11px] font-medium text-ob-muted mt-[8px] px-[10px] py-[5px] border border-ob-edge inline-block rounded-[4px] tracking-[0.04em]">
              Conditional Approval Recommended
            </div>
          </div>

          {/* Metrics */}
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <div className="font-mono text-[9px] text-ob-dim tracking-[0.14em] uppercase mb-[14px]">
              Financial Snapshot
            </div>
            <div className="grid grid-cols-2 gap-[12px]">
              <div className="p-[12px] bg-ob-glass2 border border-ob-edge rounded-[8px]">
                <div className="font-mono text-[17px] font-medium text-ob-text">₹4.2Cr</div>
                <div className="text-[10px] text-ob-muted mt-[3px] font-normal">Revenue TTM</div>
              </div>
              <div className="p-[12px] bg-ob-glass2 border border-ob-edge rounded-[8px]">
                <div className="font-mono text-[17px] font-medium text-ob-text">14.3%</div>
                <div className="text-[10px] text-ob-muted mt-[3px] font-normal">EBITDA Margin</div>
              </div>
              <div className="p-[12px] bg-ob-glass2 border border-ob-edge rounded-[8px]">
                <div className="font-mono text-[17px] font-medium text-ob-text">1.82×</div>
                <div className="text-[10px] text-ob-muted mt-[3px] font-normal">Debt / Equity</div>
              </div>
              <div className="p-[12px] bg-ob-glass2 border border-ob-edge rounded-[8px]">
                <div className="font-mono text-[17px] font-medium text-[rgba(255,180,80,0.85)]">0.93×</div>
                <div className="text-[10px] text-ob-muted mt-[3px] font-normal">DSCR ⚠</div>
              </div>
            </div>
          </div>

          {/* Research */}
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <div className="font-mono text-[9px] text-ob-dim tracking-[0.14em] uppercase mb-[14px]">
              Research Agent Findings
            </div>
            <div className="flex flex-col gap-[7px]">
              <div className="flex justify-between items-center py-[7px] border-b border-ob-edge">
                <span className="text-[11px] text-ob-muted font-normal">MCA21 Status</span>
                <span className="font-mono text-[11px] text-[rgba(255,180,80,0.8)]">1 charge registered</span>
              </div>
              <div className="flex justify-between items-center py-[7px] border-b border-ob-edge">
                <span className="text-[11px] text-ob-muted font-normal">eCourts</span>
                <span className="font-mono text-[11px] text-[rgba(180,240,180,0.7)]">No proceedings</span>
              </div>
              <div className="flex justify-between items-center py-[7px] border-b border-ob-edge">
                <span className="text-[11px] text-ob-muted font-normal">News Sentiment</span>
                <span className="font-mono text-[11px] text-[rgba(180,240,180,0.7)]">Neutral</span>
              </div>
              <div className="flex justify-between items-center pt-[7px]">
                <span className="text-[11px] text-ob-muted font-normal">Rev. Concentration</span>
                <span className="font-mono text-[11px] text-[rgba(255,180,80,0.8)]">68% top-2 clients</span>
              </div>
            </div>
          </div>

          {/* CAM */}
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <div className="font-mono text-[9px] text-ob-dim tracking-[0.14em] uppercase mb-[14px]">
              Credit Appraisal Memo
            </div>
            <div className="h-[3px] rounded-[2px] mb-[14px]" style={{ background: 'linear-gradient(90deg, rgba(255,255,255,0.2), rgba(255,255,255,0.05))' }} />

            <div className="flex justify-between text-[10px] py-[3px]">
              <span className="text-ob-muted font-normal">Borrower</span>
              <span className="font-mono text-ob-dim">Vardhman Agri Processing</span>
            </div>
            <div className="h-[1px] bg-ob-edge my-[6px]" />
            <div className="flex justify-between text-[10px] py-[3px]">
              <span className="text-ob-muted font-normal">Facility Type</span>
              <span className="font-mono text-ob-dim">Working Capital — CC</span>
            </div>
            <div className="h-[1px] bg-ob-edge my-[6px]" />
            <div className="flex justify-between text-[10px] py-[3px]">
              <span className="text-ob-muted font-normal">Recommended Limit</span>
              <span className="font-mono text-ob-dim">₹85 Lakh</span>
            </div>
            <div className="h-[1px] bg-ob-edge my-[6px]" />
            <div className="flex justify-between text-[10px] py-[3px]">
              <span className="text-ob-muted font-normal">Risk Premium</span>
              <span className="font-mono text-ob-dim">+1.25% over base</span>
            </div>

            <div className="flex justify-between items-center mt-[12px] pt-[10px] border-t border-ob-edge">
              <span className="font-mono text-[9px] text-ob-dim tracking-[0.08em]">GENERATED · 2m 34s</span>
              <span className="text-[10px] font-semibold text-ob-text cursor-pointer tracking-[0.04em]">↓ Download Word</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
