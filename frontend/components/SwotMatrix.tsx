'use client';

interface SwotItem {
  point: string;
  evidence: string;
  source: string;
}

type SwotInputItem = SwotItem | string;

interface SwotMatrixProps {
  strengths: SwotInputItem[];
  weaknesses: SwotInputItem[];
  opportunities: SwotInputItem[];
  threats: SwotInputItem[];
  investmentThesis?: string;
  recommendation?: string;
  sectorOutlook?: string;
}

export default function SwotMatrix({
  strengths,
  weaknesses,
  opportunities,
  threats,
  investmentThesis,
  recommendation,
  sectorOutlook,
}: SwotMatrixProps) {
  const renderItems = (items: SwotInputItem[], colorClass: string) =>
    items.map((item, i) => (
      <div key={i} className="mb-2.5 last:mb-0">
        {typeof item === 'string' ? (
          <p className={`text-[12px] font-medium ${colorClass}`}>{item}</p>
        ) : (
          <>
            <p className={`text-[12px] font-medium ${colorClass}`}>{item.point}</p>
            <p className="text-[11px] text-ob-muted mt-0.5 leading-relaxed">
              {item.evidence}
              {item.source && (
                <span className="font-mono text-[10px] text-ob-dim ml-1">[{item.source}]</span>
              )}
            </p>
          </>
        )}
      </div>
    ));

  return (
    <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
      <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-4">
        SWOT Analysis
      </p>

      {investmentThesis && (
        <div className="mb-4 bg-ob-glass2 border border-ob-edge rounded-[8px] p-3">
          <p className="font-mono text-[9px] text-ob-dim uppercase tracking-[0.08em] mb-1">Investment Thesis</p>
          <p className="text-[12px] text-ob-text leading-relaxed">{investmentThesis}</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Strengths */}
        <div className="bg-ob-glass2 border border-ob-ok/20 rounded-[8px] p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-5 h-5 rounded bg-ob-ok/20 flex items-center justify-center text-[11px] text-ob-ok">S</span>
            <span className="font-mono text-[11px] text-ob-ok font-medium uppercase tracking-[0.08em]">Strengths</span>
          </div>
          {strengths.length > 0 ? renderItems(strengths, 'text-ob-ok') : (
            <p className="text-[11px] text-ob-dim italic">No strengths identified</p>
          )}
        </div>

        {/* Weaknesses */}
        <div className="bg-ob-glass2 border border-ob-warn/20 rounded-[8px] p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-5 h-5 rounded bg-ob-warn/20 flex items-center justify-center text-[11px] text-ob-warn">W</span>
            <span className="font-mono text-[11px] text-ob-warn font-medium uppercase tracking-[0.08em]">Weaknesses</span>
          </div>
          {weaknesses.length > 0 ? renderItems(weaknesses, 'text-ob-warn') : (
            <p className="text-[11px] text-ob-dim italic">No weaknesses identified</p>
          )}
        </div>

        {/* Opportunities */}
        <div className="bg-ob-glass2 border border-sky-500/20 rounded-[8px] p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-5 h-5 rounded bg-sky-500/20 flex items-center justify-center text-[11px] text-sky-400">O</span>
            <span className="font-mono text-[11px] text-sky-400 font-medium uppercase tracking-[0.08em]">Opportunities</span>
          </div>
          {opportunities.length > 0 ? renderItems(opportunities, 'text-sky-400') : (
            <p className="text-[11px] text-ob-dim italic">No opportunities identified</p>
          )}
        </div>

        {/* Threats */}
        <div className="bg-ob-glass2 border border-red-500/20 rounded-[8px] p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-5 h-5 rounded bg-red-500/20 flex items-center justify-center text-[11px] text-red-400">T</span>
            <span className="font-mono text-[11px] text-red-400 font-medium uppercase tracking-[0.08em]">Threats</span>
          </div>
          {threats.length > 0 ? renderItems(threats, 'text-red-400') : (
            <p className="text-[11px] text-ob-dim italic">No threats identified</p>
          )}
        </div>
      </div>

      {/* Sector outlook + recommendation */}
      {(sectorOutlook || recommendation) && (
        <div className="mt-4 space-y-2">
          {sectorOutlook && (
            <div className="bg-ob-glass2 border border-ob-edge rounded-[8px] p-3">
              <p className="font-mono text-[9px] text-ob-dim uppercase tracking-[0.08em] mb-1">Sector Outlook</p>
              <p className="text-[11px] text-ob-muted leading-relaxed">{sectorOutlook}</p>
            </div>
          )}
          {recommendation && (
            <div className="bg-ob-glass2 border border-ob-edge rounded-[8px] p-3">
              <p className="font-mono text-[9px] text-ob-dim uppercase tracking-[0.08em] mb-1">Recommendation</p>
              <p className="text-[12px] text-ob-text leading-relaxed">{recommendation}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
