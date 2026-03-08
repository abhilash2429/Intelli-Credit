'use client';

import Link from 'next/link';

/* ── Inline SVG Icons ── */
const DocIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

const SearchIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
    <circle cx="11" cy="11" r="4" strokeDasharray="2 2" />
  </svg>
);

const ChartIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10" />
    <line x1="12" y1="20" x2="12" y2="4" />
    <line x1="6" y1="20" x2="6" y2="14" />
    <path d="M3 21h18" />
  </svg>
);

const FEATURES = [
  {
    icon: <DocIcon />,
    title: 'Multi-source ingestion',
    body: 'Upload PDFs, bank statements, GST returns, ITR files and scanned documents. OCR handles the rest.',
    tags: 'PDF · DOCX · GST · Bank CSV · ITR · JPEG',
  },
  {
    icon: <SearchIcon />,
    title: 'Autonomous research agent',
    body: 'Cross-checks MCA filings, eCourts records, news, and promoter history — without any manual lookup.',
    tags: 'MCA · eCourts · News · Promoter Intel',
  },
  {
    icon: <ChartIcon />,
    title: 'Explainable scoring + CAM',
    body: 'XGBoost ML model with SHAP-style explainability produces a decision, risk premium, and a full Credit Appraisal Memo.',
    tags: 'Five Cs · SHAP · Word/PDF CAM',
  },
];

const STEPS = [
  { num: '01', title: 'Upload Documents', desc: 'PDF, bank statements, GST, ITR, scanned pages' },
  { num: '02', title: 'Add Analyst Notes', desc: 'Site visit observations and management assessment' },
  { num: '03', title: 'Pipeline Runs', desc: 'OCR, research, scoring, CAM — fully automated' },
  { num: '04', title: 'Review & Export', desc: 'Score dashboard, explainability, downloadable memo' },
];

const MARQUEE_ITEMS = [
  'GST Returns', 'Bank Statements', 'ITR', 'Annual Reports', 'OCR Documents', 'Audit Reports',
  'Balance Sheets', 'GSTR-3B', 'Form 26AS', 'MCA Filings',
];

export default function HeroPage() {
  return (
    <div className="bg-ic-page pt-[60px]">
      {/* ── Hero Section ── */}
      <section
        className="min-h-[92vh] flex flex-col items-center justify-center px-6 text-center"
        style={{
          background: 'radial-gradient(ellipse 60% 50% at 80% 20%, rgba(44,74,46,0.06) 0%, transparent 70%)',
        }}
      >
        {/* Eyebrow */}
        <p className="text-[10px] font-medium tracking-[0.16em] uppercase text-ic-accent mb-5">
          AI-Powered Credit Appraisal
        </p>

        {/* Headline */}
        <h1 className="font-display text-[58px] font-semibold text-ic-text leading-[1.1] max-w-[680px]">
          Assess any borrower.{' '}
          <br />
          In <span className="italic text-ic-accent">minutes</span>.
        </h1>

        {/* Subheading */}
        <p className="text-[16px] text-ic-muted leading-[1.7] max-w-[520px] mt-6">
          Intelli·Credit combines document intelligence, autonomous web research, and ML-powered scoring
          to produce a bank-grade Credit Appraisal Memo — automatically.
        </p>

        {/* CTA Row */}
        <div className="flex items-center gap-5 mt-9">
          <Link
            href="/app/start"
            className="px-7 py-3.5 bg-ic-accent text-white text-[14px] font-medium rounded-[8px] no-underline transition-opacity hover:opacity-90"
          >
            Get Started →
          </Link>
          <a
            href="#how-it-works"
            className="text-ic-accent text-[14px] underline underline-offset-4 decoration-1"
          >
            See how it works
          </a>
        </div>

        {/* Trust chips */}
        <p className="text-[11px] text-ic-muted mt-6">
          ✓ No login required · ✓ Indian lending context · ✓ Generates CAM in minutes
        </p>
      </section>

      {/* ── Social Proof Strip ── */}
      <div className="bg-ic-surface-mid border-y border-ic-border py-4 overflow-hidden">
        <div className="flex animate-marquee whitespace-nowrap">
          {[...MARQUEE_ITEMS, ...MARQUEE_ITEMS].map((item, i) => (
            <span key={i} className="font-mono text-[11px] text-ic-muted tracking-[0.06em] mx-4">
              {item}
            </span>
          ))}
        </div>
        <style jsx>{`
          @keyframes marquee {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
          }
          .animate-marquee {
            animation: marquee 30s linear infinite;
          }
        `}</style>
      </div>

      {/* ── Feature Highlights ── */}
      <section id="how-it-works" className="py-20 px-6">
        <div className="max-w-[1100px] mx-auto text-center">
          <h2 className="font-display text-[36px] text-ic-text">From documents to decision</h2>
          <p className="text-[14px] text-ic-muted max-w-[480px] mx-auto mt-3">
            Three stages that transform raw financial documents into an actionable credit appraisal.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-12">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="bg-ic-surface border border-ic-border rounded-[12px] p-6 text-left transition-all duration-200 hover:shadow-sm hover:-translate-y-0.5"
              >
                <div className="w-10 h-10 bg-ic-accent-light rounded-[8px] flex items-center justify-center text-ic-accent">
                  {f.icon}
                </div>
                <h3 className="font-display text-[18px] text-ic-text mt-4">{f.title}</h3>
                <p className="text-[13px] text-ic-muted leading-[1.7] mt-2">{f.body}</p>
                <p className="font-mono text-[10px] text-ic-muted mt-4">{f.tags}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pipeline Steps ── */}
      <section className="py-16 px-6 bg-ic-surface-mid">
        <div className="max-w-[900px] mx-auto text-center">
          <h2 className="font-display text-[32px] text-ic-text">How it works</h2>
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between mt-12 gap-6">
            {STEPS.map((step, i) => (
              <div key={step.num} className="flex md:flex-col items-center md:items-center gap-3 md:gap-0 flex-1 text-center">
                {/* Circle */}
                <div className="w-10 h-10 rounded-full border-2 border-ic-accent text-ic-accent flex items-center justify-center text-[13px] font-mono font-medium shrink-0">
                  {step.num}
                </div>
                <div className="md:mt-3">
                  <p className="text-[13px] font-medium text-ic-text">{step.title}</p>
                  <p className="text-[11px] text-ic-muted mt-1">{step.desc}</p>
                </div>
                {/* Connector line (hidden on last, visible on desktop) */}
                {i < STEPS.length - 1 && (
                  <div className="hidden md:block absolute" />
                )}
              </div>
            ))}
          </div>
          {/* Connector lines between steps on desktop */}
          <div className="hidden md:flex max-w-[700px] mx-auto mt-[-52px] mb-[40px] items-center px-[60px]">
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex-1 h-px bg-ic-border" />
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="py-20 px-6 text-center">
        <h2 className="font-display text-[32px] text-ic-text">
          Ready to assess your first borrower?
        </h2>
        <Link
          href="/app/start"
          className="inline-block mt-6 px-7 py-3.5 bg-ic-accent text-white text-[14px] font-medium rounded-[8px] no-underline transition-opacity hover:opacity-90"
        >
          Get Started →
        </Link>
        <p className="text-[11px] text-ic-muted mt-4">
          No account needed. Your data stays local.
        </p>
      </section>
    </div>
  );
}
