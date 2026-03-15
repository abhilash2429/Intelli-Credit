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
              href="/app/login"
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

        {/* RIGHT — feature highlights */}
        <div className={`w-full lg:w-[360px] shrink-0 flex flex-col gap-[10px] pt-1 transition-all duration-1000 delay-300 transform ${mounted ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0'}`}>
          {/* Pipeline coverage */}
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <div className="font-mono text-[9px] text-ob-dim tracking-[0.14em] uppercase mb-[14px]">
              Document Intelligence
            </div>
            <div className="grid grid-cols-2 gap-[8px]">
              {['ALM Statement', 'Shareholding', 'Borrowing Profile', 'Annual Reports', 'Portfolio Data', 'Bank Statement', 'GST Returns', 'ITR / PAN'].map((doc) => (
                <div key={doc} className="flex items-center gap-2 p-[10px] bg-ob-glass2 border border-ob-edge rounded-[6px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-ob-ok flex-shrink-0" />
                  <span className="font-mono text-[10px] text-ob-muted">{doc}</span>
                </div>
              ))}
            </div>
          </div>

          {/* AI capabilities */}
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <div className="font-mono text-[9px] text-ob-dim tracking-[0.14em] uppercase mb-[14px]">
              AI Research Engine
            </div>
            <div className="flex flex-col gap-[7px]">
              {[
                { label: 'Web Scraping', value: 'Crawl4AI + Live', ok: true },
                { label: 'MCA21 Lookup', value: 'Auto', ok: true },
                { label: 'eCourts Search', value: 'Auto', ok: true },
                { label: 'News Sentiment', value: 'NLP Classified', ok: true },
                { label: 'Fraud Graph', value: 'Multi-signal', ok: true },
              ].map(({ label, value, ok }) => (
                <div key={label} className="flex justify-between items-center py-[6px] border-b border-ob-edge last:border-0">
                  <span className="text-[11px] text-ob-muted font-normal">{label}</span>
                  <span className={`font-mono text-[11px] ${ok ? 'text-[rgba(180,240,180,0.8)]' : 'text-[rgba(255,180,80,0.8)]'}`}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Output */}
          <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
            <div className="font-mono text-[9px] text-ob-dim tracking-[0.14em] uppercase mb-[14px]">
              Output & Analysis
            </div>
            <div className="flex flex-col gap-[7px]">
              {[
                { label: 'Credit Score', value: '300 – 900 scale' },
                { label: 'Risk Grade', value: 'AAA → D' },
                { label: 'SHAP Explainability', value: 'Per factor' },
                { label: 'SWOT Analysis', value: 'AI-generated' },
                { label: 'CAM Report', value: 'Word / PDF' },
                { label: 'Chat with CAM', value: 'Gemini AI' },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between items-center py-[6px] border-b border-ob-edge last:border-0">
                  <span className="text-[11px] text-ob-muted font-normal">{label}</span>
                  <span className="font-mono text-[11px] text-ob-dim">{value}</span>
                </div>
              ))}
            </div>
            <div className="mt-[14px] pt-[12px] border-t border-ob-edge">
              <Link
                href="/app/login"
                className="block w-full text-center bg-ob-text text-ob-bg font-body text-[12px] font-bold px-4 py-[10px] rounded-[6px] tracking-[0.04em] no-underline hover:bg-ob-cream transition-all duration-200"
              >
                Start an Assessment →
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
