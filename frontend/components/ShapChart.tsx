'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from 'recharts';

interface ShapEntry {
  feature: string;
  value: number;
  direction: string;
}

const FEATURE_LABELS: Record<string, string> = {
  dscr: 'Debt Service Coverage',
  ebitda_margin_pct: 'EBITDA Margin %',
  current_ratio: 'Current Ratio',
  debt_to_equity: 'Debt-to-Equity',
  revenue_growth_yoy: 'Revenue Growth YoY',
  gst_bank_mismatch_pct: 'GST-Bank Mismatch %',
  active_litigation_count: 'Active Litigation',
  promoter_red_flag: 'Promoter Red Flag',
  factory_capacity_pct: 'Factory Capacity %',
  auditor_qualified: 'Auditor Qualified',
  charge_count: 'MCA Charge Count',
  bounced_cheques_12m: 'Bounced Cheques (12m)',
  sector_risk_index: 'Sector Risk Index',
};

export default function ShapChart({ data }: { data: ShapEntry[] }) {
  const chartData = data.map((d) => ({
    ...d,
    label: FEATURE_LABELS[d.feature] || d.feature,
  }));

  return (
    <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
      <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">
        SHAP Feature Importance
      </p>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 160, right: 30 }}>
          <XAxis
            type="number"
            tick={{ fill: 'var(--ob-muted)', fontSize: 11, fontFamily: 'DM Mono, monospace' }}
          />
          <YAxis
            type="category"
            dataKey="label"
            tick={{ fill: 'var(--ob-text)', fontSize: 12, fontFamily: 'Manrope, sans-serif' }}
            width={150}
          />
          <Tooltip
            formatter={(value: number) => value.toFixed(3)}
            contentStyle={{
              backgroundColor: 'var(--ob-surface)',
              border: '1px solid var(--ob-edge)',
              borderRadius: '8px',
              color: 'var(--ob-text)',
              fontFamily: 'DM Mono, monospace',
            }}
          />
          <ReferenceLine x={0} stroke="var(--ob-edge)" />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.value > 0 ? 'var(--ob-text)' : 'var(--ob-warn)'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="flex gap-6 mt-3 text-[12px]">
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 bg-ob-text rounded" /> Risk Increase
        </span>
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 bg-ob-warn rounded" /> Risk Decrease
        </span>
      </div>
    </div>
  );
}
