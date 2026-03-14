'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { animate, AnimatePresence, motion } from 'framer-motion';
import { Activity, ChevronDown, Factory, ShieldCheck } from 'lucide-react';
import { useAnalysisStore } from '@/store/analysisStore';
import { getResultsV1 } from '@/lib/api';
import { formatCurrencyCr, formatPercentage, formatRatio } from '@/lib/formatters';

const GAUGE_RADIUS = 160;
const GAUGE_CX = 200;
const GAUGE_CY = 220;
const ARC_LEN = Math.PI * GAUGE_RADIUS;

function getNeedlePoint(score: number) {
  const clamped = Math.max(0, Math.min(100, score));
  const angleDeg = -180 + (clamped / 100) * 180;
  const rad = (angleDeg * Math.PI) / 180;
  return {
    x: GAUGE_CX + (GAUGE_RADIUS - 28) * Math.cos(rad),
    y: GAUGE_CY + (GAUGE_RADIUS - 28) * Math.sin(rad),
  };
}

export default function ScorePage() {
  const { result, companyId, companyName, setResult } = useAnalysisStore();
  const [loading, setLoading] = useState(false);
  const [animatedScore, setAnimatedScore] = useState(0);
  const [scoreSettled, setScoreSettled] = useState(false);
  const [showExplanation, setShowExplanation] = useState(false);
  const [typedExplanation, setTypedExplanation] = useState('');
  const [ripple, setRipple] = useState<{ x: number; y: number; id: number } | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (companyId && (!result || !result.decision)) {
      setLoading(true);
      getResultsV1(companyId)
        .then((res) => setResult(res.data))
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [companyId, result, setResult]);

  const score = useMemo(() => {
    if (!result) return null;
    const decision = result.decision || {};
    const explanation = result.explanation || {};
    const features = result.features || {};

    const rawScore = Number(decision.credit_score || 0);
    const normalizedScore = Number(
      decision.normalized_score ?? (rawScore ? (rawScore / 900) * 100 : 0)
    );
    if (!normalizedScore) return null;

    return {
      companyName: companyName || 'Bharat Industries Limited',
      industry: String(result?.company?.sector || 'Manufacturing'),
      requestedLoanCr: Number(result?.loan?.loan_amount_cr || decision.recommended_loan_amount || 500),
      finalRiskScore: Math.max(0, Math.min(100, normalizedScore)),
      riskCategory: String(decision.risk_grade || decision.risk_category || 'AAA'),
      dscr: Number(features.dscr ?? 1.44),
      gstMismatchPct: Number(result?.gst_mismatch?.itc_inflation_percentage ?? 0),
      capacityUtilizationPct: Number(features.factory_capacity_utilization ?? 65),
      rationale:
        String(explanation.decision_narrative || decision.decision_rationale || '').trim() ||
        'This company demonstrates strong compliance signals and stable operating cashflows. GST reconciliation shows no discrepancies and debt servicing capacity remains above acceptable thresholds.',
    };
  }, [companyName, result]);

  useEffect(() => {
    if (!score) return;
    setScoreSettled(false);
    setAnimatedScore(0);
    const controls = animate(0, score.finalRiskScore, {
      duration: 1.8,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setAnimatedScore(v),
      onComplete: () => setScoreSettled(true),
    });
    return () => controls.stop();
  }, [score]);

  useEffect(() => {
    if (!score || !showExplanation) return;
    setTypedExplanation('');
    const fullText = score.rationale;
    let index = 0;
    const timer = window.setInterval(() => {
      index += 1;
      setTypedExplanation(fullText.slice(0, index));
      if (index >= fullText.length) {
        window.clearInterval(timer);
      }
    }, 16);
    return () => window.clearInterval(timer);
  }, [score, showExplanation]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-56px)] bg-[#0B0B0C]">
        <p className="text-[#9CA3AF] animate-pulse">Loading credit risk dashboard...</p>
      </div>
    );
  }

  if (!result || !result.decision || !score) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100vh-56px)] bg-[#0B0B0C] px-4">
        <div className="text-center space-y-3">
          <p className="text-[#9CA3AF] text-base">Score not yet available.</p>
          <p className="text-[#9CA3AF] text-[13px]">
            Run the analysis pipeline first and wait for completion in Results.
          </p>
          <button
            onClick={() => router.push('/app/results')}
            className="px-4 py-2 rounded-md border border-white/20 text-white hover:bg-white/5 transition-colors"
          >
            Go To Results
          </button>
        </div>
      </div>
    );
  }

  const needle = getNeedlePoint(animatedScore);
  const progress = (Math.max(0, Math.min(100, animatedScore)) / 100) * ARC_LEN;
  const statusLabel = `${score.riskCategory} - Low Risk`;
  const metrics = [
    {
      title: 'DSCR',
      icon: Activity,
      value: formatRatio(score.dscr),
      status: 'Stable',
      description: 'Debt servicing capacity is above minimum underwriting threshold.',
    },
    {
      title: 'GST Compliance',
      icon: ShieldCheck,
      value: `${formatPercentage(score.gstMismatchPct)} mismatch`,
      status: 'Excellent',
      description: 'Tax credit reconciliation is clean with no anomaly signals.',
    },
    {
      title: 'Factory Utilization',
      icon: Factory,
      value: formatPercentage(score.capacityUtilizationPct),
      status: 'Moderate',
      description: 'Capacity is healthy but still has room for operational upside.',
    },
  ];

  const particleNodes = Array.from({ length: 18 }, (_, i) => ({
    id: i,
    left: `${(i * 13 + 7) % 100}%`,
    top: `${(i * 19 + 11) % 100}%`,
    duration: 5 + (i % 6),
  }));

  return (
    <div className="relative min-h-[calc(100vh-56px)] overflow-hidden bg-[#0B0B0C] px-4 py-10 md:px-8">
      <div
        className="pointer-events-none absolute inset-0 opacity-30"
        style={{
          backgroundImage:
            'linear-gradient(rgba(156,163,175,0.09) 1px, transparent 1px), linear-gradient(90deg, rgba(156,163,175,0.09) 1px, transparent 1px)',
          backgroundSize: '44px 44px',
        }}
      />
      <div className="pointer-events-none absolute inset-0">
        {particleNodes.map((p) => (
          <motion.span
            key={p.id}
            className="absolute h-1 w-1 rounded-full bg-[#2ECC71]/40"
            style={{ left: p.left, top: p.top }}
            animate={{ y: [0, -12, 0], opacity: [0.2, 0.75, 0.2] }}
            transition={{ duration: p.duration, repeat: Infinity, ease: 'easeInOut' }}
          />
        ))}
      </div>

      <div className="relative mx-auto max-w-[1040px]">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 shadow-[0_20px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl"
        >
          <div className="grid gap-3 md:grid-cols-4 md:items-center">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Company</p>
              <p className="mt-1 text-lg font-semibold text-white">{score.companyName}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Industry</p>
              <p className="mt-1 text-lg font-semibold text-white">{score.industry}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Loan Requested</p>
              <p className="mt-1 text-lg font-semibold text-white">{formatCurrencyCr(score.requestedLoanCr)}</p>
            </div>
            <div className="flex md:justify-end">
              <span className="inline-flex rounded-full border border-[#2ECC71]/40 bg-[#2ECC71]/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-[#2ECC71]">
                {statusLabel}
              </span>
            </div>
          </div>
        </motion.div>

        <div className="relative mt-8 flex flex-col items-center">
          <motion.div whileHover={{ rotate: [0, 1.1, -1.1, 0] }} transition={{ duration: 0.6 }}>
            <div className="relative">
              {scoreSettled && (
                <motion.div
                  className="pointer-events-none absolute inset-7 rounded-full border border-[#2ECC71]/30"
                  initial={{ opacity: 0.1, scale: 0.95 }}
                  animate={{ opacity: [0.1, 0.35, 0.1], scale: [0.95, 1.05, 0.95] }}
                  transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
                />
              )}
              <svg width="400" height="250" viewBox="0 0 400 250">
                <defs>
                  <linearGradient id="riskGradient" x1="40" y1="220" x2="360" y2="220">
                    <stop offset="0%" stopColor="#ef4444" />
                    <stop offset="50%" stopColor="#facc15" />
                    <stop offset="100%" stopColor="#2ECC71" />
                  </linearGradient>
                </defs>

                <path
                  d="M 40 220 A 160 160 0 0 1 360 220"
                  stroke="rgba(255,255,255,0.12)"
                  strokeWidth="24"
                  strokeLinecap="round"
                  fill="none"
                />
                <motion.path
                  d="M 40 220 A 160 160 0 0 1 360 220"
                  stroke="url(#riskGradient)"
                  strokeWidth="24"
                  strokeLinecap="round"
                  fill="none"
                  strokeDasharray={`${progress} ${ARC_LEN}`}
                />

                <line
                  x1={GAUGE_CX}
                  y1={GAUGE_CY}
                  x2={needle.x}
                  y2={needle.y}
                  stroke="#ffffff"
                  strokeWidth="3"
                  strokeLinecap="round"
                />
                <circle cx={GAUGE_CX} cy={GAUGE_CY} r="8" fill="#ffffff" />
              </svg>
            </div>
          </motion.div>

          <motion.p
            className="mt-[-14px] text-6xl font-semibold tracking-tight text-white"
            animate={{ textShadow: scoreSettled ? '0 0 26px rgba(46,204,113,0.28)' : '0 0 0px rgba(46,204,113,0)' }}
          >
            {Math.round(animatedScore)}
          </motion.p>
          <p className="mt-1 text-sm uppercase tracking-[0.28em] text-[#9CA3AF]">Credit Risk Score</p>
        </div>

        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {metrics.map((metric, idx) => {
            const Icon = metric.icon;
            return (
              <motion.div
                key={metric.title}
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 + idx * 0.1, duration: 0.55 }}
                whileHover={{ y: -5, scale: 1.01 }}
                className="group rounded-xl border border-white/10 bg-white/[0.04] p-5 shadow-[0_8px_28px_rgba(0,0,0,0.35)] backdrop-blur-md"
              >
                <div className="flex items-center justify-between">
                  <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">{metric.title}</p>
                  <Icon className="h-4 w-4 text-[#2ECC71]" />
                </div>
                <p className="mt-3 text-2xl font-semibold text-white">{metric.value}</p>
                <p className="mt-1 text-sm text-[#2ECC71]">{metric.status}</p>
                <p className="mt-3 text-xs leading-relaxed text-[#9CA3AF] opacity-0 transition-opacity duration-200 group-hover:opacity-100">
                  {metric.description}
                </p>
              </motion.div>
            );
          })}
        </div>

        <div className="mt-8 rounded-xl border border-white/10 bg-white/[0.04] backdrop-blur-md">
          <button
            onClick={() => setShowExplanation((prev) => !prev)}
            className="flex w-full items-center justify-between px-5 py-4 text-left"
          >
            <span className="text-sm font-semibold uppercase tracking-[0.18em] text-white">
              AI Risk Explanation
            </span>
            <ChevronDown
              className={`h-4 w-4 text-[#9CA3AF] transition-transform ${showExplanation ? 'rotate-180' : ''}`}
            />
          </button>
          <AnimatePresence initial={false}>
            {showExplanation && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.35 }}
                className="overflow-hidden border-t border-white/10"
              >
                <p className="px-5 py-4 text-[14px] leading-relaxed text-[#E5E7EB]">{typedExplanation}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="mt-8 flex justify-center">
          <motion.button
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              setRipple({
                x: e.clientX - rect.left,
                y: e.clientY - rect.top,
                id: Date.now(),
              });
              window.setTimeout(() => setRipple(null), 520);
              router.push('/app/results');
            }}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.985 }}
            animate={{
              boxShadow: [
                '0 0 0px rgba(46,204,113,0.25)',
                '0 0 28px rgba(46,204,113,0.3)',
                '0 0 0px rgba(46,204,113,0.25)',
              ],
            }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
            className="relative overflow-hidden rounded-xl border border-[#2ECC71]/40 bg-[#2ECC71]/20 px-10 py-3 text-sm font-bold tracking-[0.22em] text-white"
          >
            APPROVE LOAN
            {ripple && (
              <motion.span
                key={ripple.id}
                className="pointer-events-none absolute rounded-full bg-white/50"
                style={{ left: ripple.x, top: ripple.y }}
                initial={{ width: 0, height: 0, opacity: 0.7, x: '-50%', y: '-50%' }}
                animate={{ width: 240, height: 240, opacity: 0 }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            )}
          </motion.button>
        </div>
      </div>
    </div>
  );
}
