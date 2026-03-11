'use client';

interface TimelineItem {
  timestamp: string;
  title: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
  details?: string;
}

const severityStyle: Record<TimelineItem['severity'], { dot: string; badge: string }> = {
  CRITICAL: { dot: 'bg-ob-warn', badge: 'bg-ob-warn-bg text-ob-warn border border-ob-warn-edge' },
  HIGH: { dot: 'bg-ob-warn', badge: 'bg-ob-warn-bg text-ob-warn border border-ob-warn-edge' },
  MEDIUM: { dot: 'bg-ob-edge2', badge: 'bg-ob-glass2 text-ob-muted border border-ob-edge' },
  LOW: { dot: 'bg-ob-text', badge: 'bg-ob-glass2 text-ob-ok border border-ob-ok-edge' },
  INFORMATIONAL: { dot: 'bg-ob-muted', badge: 'bg-ob-glass2 text-ob-muted border border-ob-edge' },
};

export default function TimelineView({ items }: { items: TimelineItem[] }) {
  return (
    <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
      <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-4">Risk Flag Timeline</p>
      <div className="space-y-0">
        {items.map((item, idx) => {
          const styles = severityStyle[item.severity] || severityStyle.INFORMATIONAL;
          return (
            <div key={`${item.timestamp}-${idx}`} className="flex gap-3 py-2.5 border-b border-ob-edge last:border-0">
              <div className={`w-2.5 h-2.5 rounded-full mt-1 flex-shrink-0 ${styles.dot}`} />
              <div className="flex-1 min-w-0">
                <p className="font-mono text-[11px] text-ob-muted">{new Date(item.timestamp).toLocaleString()}</p>
                <p className="text-[13px] font-medium text-ob-text mt-0.5">{item.title}</p>
                {item.details && <p className="text-ob-muted text-[12px] mt-0.5">{item.details}</p>}
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded font-medium h-fit flex-shrink-0 ${styles.badge}`}>
                {item.severity}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
