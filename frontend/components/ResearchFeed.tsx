'use client';

import { useMemo, useState } from 'react';

interface Finding {
  source_url: string;
  source_name: string;
  finding_type: string;
  summary: string;
  severity: string;
  date_of_finding?: string | null;
  raw_snippet: string;
}

const FILTERS = ['ALL', 'CRITICAL', 'FRAUD', 'LITIGATION', 'SECTOR'] as const;

export default function ResearchFeed({ findings }: { findings: Finding[] }) {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>('ALL');

  const hasMockData = useMemo(
    () => findings.some((f) => f.source_name.includes('Mock')),
    [findings]
  );

  const filtered = useMemo(() => {
    if (filter === 'ALL') return findings;
    if (filter === 'CRITICAL') return findings.filter((f) => f.severity === 'CRITICAL');
    if (filter === 'FRAUD') return findings.filter((f) => f.finding_type === 'FRAUD_ALERT');
    if (filter === 'LITIGATION') return findings.filter((f) => f.finding_type === 'LITIGATION');
    if (filter === 'SECTOR') return findings.filter((f) => f.finding_type === 'SECTOR');
    return findings;
  }, [filter, findings]);

  const getSeverityStyle = (severity: string) => {
    if (severity === 'CRITICAL') return 'bg-ob-warn-bg text-ob-warn border border-ob-warn-edge';
    if (severity === 'HIGH') return 'bg-ob-warn-bg text-ob-warn border border-ob-warn-edge';
    return 'bg-ob-glass2 text-ob-muted border border-ob-edge';
  };

  return (
    <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
      <div className="flex items-center justify-between mb-4">
        <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim">Research Feed</p>
        <div className="flex gap-1.5 flex-wrap">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-1 rounded text-[10px] font-medium transition-colors ${filter === f
                ? 'bg-ob-text text-ob-bg font-bold'
                : 'bg-ob-glass2 text-ob-muted hover:text-ob-text'
                }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {hasMockData && (
        <div className="mb-3 px-3 py-2 rounded bg-ob-glass2 border border-ob-edge text-[11px] text-ob-muted font-medium">
          ℹ️ Live web research unavailable — results shown are from cached regulatory data.
          To enable live search, add <span className="font-mono text-ob-text">TAVILY_API_KEY</span> and/or <span className="font-mono text-ob-text">FIRECRAWL_API_KEY</span> to your <span className="font-mono text-ob-text">.env</span> file.
        </div>
      )}

      <div className="space-y-0 max-h-[420px] overflow-auto">
        {filtered.map((f, idx) => (
          <div key={`${f.source_url}-${idx}`} className="py-2.5 border-b border-ob-edge last:border-0">
            <div className="flex justify-between items-start gap-2">
              <p className="text-[13px] font-medium text-ob-text">{f.source_name}</p>
              <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${getSeverityStyle(f.severity)}`}>
                {f.severity}
              </span>
            </div>
            <p className="text-ob-muted text-[12px] mt-1">{f.summary}</p>
            <div className="flex items-center gap-3 mt-1.5">
              <span className="font-mono text-[11px] text-ob-muted">
                {f.date_of_finding ? new Date(f.date_of_finding).toLocaleDateString() : 'No date'}
              </span>
              <a
                href={f.source_url}
                target="_blank"
                rel="noreferrer"
                className="text-ob-text text-[11px] no-underline hover:underline"
              >
                Source →
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
