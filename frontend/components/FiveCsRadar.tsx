'use client';

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Legend,
  Tooltip,
} from 'recharts';

interface Props {
  company: {
    character: number;
    capacity: number;
    capital: number;
    collateral: number;
    conditions: number;
  };
  benchmark?: {
    character: number;
    capacity: number;
    capital: number;
    collateral: number;
    conditions: number;
  };
}

export default function FiveCsRadar({ company, benchmark }: Props) {
  const b = benchmark || {
    character: 7.2,
    capacity: 7.0,
    capital: 6.8,
    collateral: 6.5,
    conditions: 6.9,
  };

  const data = [
    { metric: 'Character', company: company.character, benchmark: b.character },
    { metric: 'Capacity', company: company.capacity, benchmark: b.capacity },
    { metric: 'Capital', company: company.capital, benchmark: b.capital },
    { metric: 'Collateral', company: company.collateral, benchmark: b.collateral },
    { metric: 'Conditions', company: company.conditions, benchmark: b.conditions },
  ];

  return (
    <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
      <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Five Cs Radar</p>
      <ResponsiveContainer width="100%" height={360}>
        <RadarChart data={data}>
          <PolarGrid stroke="var(--ob-edge)" />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fill: 'var(--ob-muted)', fontSize: 11, fontFamily: 'Manrope, sans-serif' }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 10]}
            tick={{ fill: 'var(--ob-muted)', fontSize: 11, fontFamily: 'DM Mono, monospace' }}
          />
          <Radar
            name="Company Score"
            dataKey="company"
            stroke="var(--ob-text)"
            fill="var(--ob-text)"
            fillOpacity={0.15}
          />
          <Radar
            name="Industry Benchmark"
            dataKey="benchmark"
            stroke="var(--ob-edge2)"
            fill="var(--ob-edge2)"
            fillOpacity={0.1}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--ob-surface)',
              border: '1px solid var(--ob-edge)',
              color: 'var(--ob-text)',
              fontFamily: 'DM Mono, monospace',
            }}
          />
          <Legend wrapperStyle={{ color: 'var(--ob-text)', fontSize: 12 }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
