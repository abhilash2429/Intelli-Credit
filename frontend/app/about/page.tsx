'use client';

const PIPELINE_STAGES = [
  { title: 'Multi-Source Data Input', desc: 'PDFs, bank statements, GST XML, ITR JSON, scanned images' },
  { title: 'Document Processing', desc: 'fitz + pdfplumber + Qwen2.5-VL OCR for 22 Indian languages' },
  { title: 'Structured Knowledge Store', desc: 'PostgreSQL for structured data, Qdrant for semantic vectors' },
  { title: 'Web Research Agent', desc: 'Firecrawl-powered autonomous MCA, eCourts, news, promoter checks' },
  { title: 'Risk Scoring Engine', desc: 'XGBoost model + hard rejection rules + SHAP explainability' },
  { title: 'CAM Generator', desc: '9-section Credit Appraisal Memo in Word/PDF with banking layout' },
  { title: 'Credit Officer Portal', desc: 'Interactive dashboard with Five Cs radar, stress test, RAG chat' },
];

const TECH_STACK = [
  { name: 'Next.js 14', role: 'Frontend framework (App Router)' },
  { name: 'FastAPI', role: 'Backend API with async endpoints' },
  { name: 'PostgreSQL', role: 'Structured data and company records' },
  { name: 'Qdrant', role: 'Vector store for RAG retrieval' },
  { name: 'XGBoost', role: 'ML risk scoring model' },
  { name: 'Firecrawl', role: 'Web research and scraping' },
  { name: 'Celery', role: 'Async task queue for pipeline' },
  { name: 'Delta Lake', role: 'Data versioning via Databricks' },
  { name: 'Qwen2.5-VL', role: 'OCR for scanned documents' },
  { name: 'Prefect', role: 'Workflow orchestration' },
];

const INDIA_CHIPS = [
  'GST/GSTR parsing',
  'ITR + Form 26AS',
  'MCA21 checks',
  'eCourts verification',
];

export default function AboutPage() {
  return (
    <div className="bg-ic-page pt-[60px]">
      <div className="max-w-[900px] mx-auto py-20 px-4 md:px-8">
        {/* Page Header */}
        <p className="text-[10px] font-medium tracking-[0.16em] uppercase text-ic-accent">
          About Intelli·Credit
        </p>
        <h1 className="font-display text-[42px] font-normal text-ic-text mt-3 leading-tight">
          Built for Indian credit officers
        </h1>
        <p className="text-[15px] text-ic-muted leading-[1.8] mt-4 max-w-[640px]">
          Intelli·Credit is an end-to-end AI-powered credit appraisal engine designed for Indian corporate lending workflows.
          It processes financial documents, conducts autonomous web research, and generates explainable credit decisions.
        </p>

        {/* What it does — Editorial prose */}
        <div className="mt-12 border-l-2 border-ic-border pl-6 space-y-5">
          <p className="text-[15px] text-ic-text leading-[1.85]">
            <strong>Document Intelligence.</strong> Upload annual reports, bank statements, GST returns, ITR filings,
            and scanned pages. The system uses a multi-model OCR pipeline — fitz, pdfplumber, and Qwen2.5-VL — to
            extract structured data from any format, in 22 Indian languages. Cross-validation catches inconsistencies
            between GST, bank, and tax return data automatically.
          </p>
          <p className="text-[15px] text-ic-text leading-[1.85]">
            <strong>Autonomous Research Agent.</strong> A Firecrawl-powered agent searches MCA21 filings, eCourts
            litigation records, news articles, and promoter intelligence — producing a structured research dossier
            without any manual lookup. Findings are classified by severity and integrated into the risk assessment.
          </p>
          <p className="text-[15px] text-ic-text leading-[1.85]">
            <strong>Scoring &amp; CAM Generation.</strong> An XGBoost ML model combined with configurable policy rules
            produces a credit score, risk grade, recommended loan amount, and interest premium. Every decision is
            SHAP-explainable. The system then generates a complete 9-section Credit Appraisal Memorandum in Word and PDF.
          </p>
        </div>

        {/* Architecture — Visual Pipeline */}
        <div className="mt-16 bg-ic-surface border border-ic-border rounded-[12px] p-8">
          <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ic-muted mb-6">Architecture Pipeline</p>
          <div className="space-y-0">
            {PIPELINE_STAGES.map((stage, idx) => {
              const isLast = idx === PIPELINE_STAGES.length - 1;
              return (
                <div key={stage.title} className="flex gap-4">
                  {/* Left column: icon + connector */}
                  <div className="flex flex-col items-center">
                    <div className="w-[30px] h-[30px] bg-ic-accent-light rounded-[6px] flex items-center justify-center text-ic-accent text-[11px] font-mono font-medium flex-shrink-0">
                      {idx + 1}
                    </div>
                    {!isLast && <div className="w-px flex-1 bg-ic-border ml-0" />}
                  </div>
                  {/* Right column: content */}
                  <div className="pb-5">
                    <p className="text-[13px] font-medium text-ic-text">{stage.title}</p>
                    <p className="text-[12px] text-ic-muted mt-0.5">{stage.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Tech Stack */}
        <div className="mt-12">
          <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ic-muted mb-4">Tech Stack</p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {TECH_STACK.map((t) => (
              <div key={t.name} className="bg-ic-surface-mid rounded-[8px] p-4">
                <p className="font-mono text-[13px] text-ic-text">{t.name}</p>
                <p className="text-[11px] text-ic-muted mt-1">{t.role}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Indian Lending Context */}
        <div className="mt-12">
          <h2 className="font-display text-[22px] text-ic-text">Built for Indian workflows</h2>
          <div className="flex flex-wrap gap-2 mt-4">
            {INDIA_CHIPS.map((chip) => (
              <span
                key={chip}
                className="bg-ic-accent-light text-ic-accent rounded-full px-4 py-1.5 text-[12px] font-medium"
              >
                {chip}
              </span>
            ))}
          </div>
        </div>

        {/* Data Handling Note */}
        <div className="mt-8 bg-ic-surface-mid border border-ic-border rounded-[10px] p-5 flex gap-3">
          <svg className="w-5 h-5 text-ic-muted flex-shrink-0 mt-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <p className="text-[13px] text-ic-muted leading-[1.7]">
            Your documents are processed locally and never stored on external servers. All analysis runs within your own deployment.
          </p>
        </div>
      </div>
    </div>
  );
}
