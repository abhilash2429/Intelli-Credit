'use client';

interface Anomaly {
  title: string;
  details: string;
  severity: string;
}

const getTagStyle = (severity: string) => {
  if (severity === 'CRITICAL' || severity === 'HIGH')
    return 'bg-ob-warn-bg text-ob-warn border border-ob-warn-edge';
  if (severity === 'LOW' || severity === 'POSITIVE')
    return 'bg-ob-glass2 text-ob-ok border border-ob-ok-edge';
  return 'bg-ob-glass2 text-ob-muted border border-ob-edge';
};

export default function AnomalyFlags({ anomalies }: { anomalies: Anomaly[] }) {
  if (!anomalies.length) {
    return (
      <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
        <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Anomaly Flags</p>
        <p className="text-ob-muted text-[13px]">No anomaly or fraud flags detected.</p>
      </div>
    );
  }

  return (
    <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-5">
      <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-4">Anomaly Flags</p>
      <div className="space-y-3">
        {anomalies.map((a, idx) => (
          <div key={`${a.title}-${idx}`} className="py-2.5 border-b border-ob-edge last:border-0">
            <p className="text-[13px] font-medium text-ob-text">{a.title}</p>
            <p className="text-ob-muted text-[12px] mt-1">{a.details}</p>
            <span className={`inline-block mt-2 text-[10px] px-2 py-0.5 rounded font-medium ${getTagStyle(a.severity)}`}>
              {a.severity}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
