'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAnalysisStore } from '@/store/analysisStore';
import {
  ClassificationItem,
  getClassifications,
  updateClassification,
  extractSchema,
} from '@/lib/api';

const DOC_TYPES = [
  'ANNUAL_REPORT', 'ALM_STATEMENT', 'SHAREHOLDING_PATTERN', 'BORROWING_PROFILE',
  'PORTFOLIO_QUALITY', 'GST_FILING', 'BANK_STATEMENT', 'ITR', 'FINANCIAL_STATEMENT',
  'RATING_REPORT', 'LEGAL_NOTICE', 'SANCTION_LETTER', 'OTHER',
];

export default function ClassifyPage() {
  const router = useRouter();
  const { companyId } = useAnalysisStore();
  const [items, setItems] = useState<ClassificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [overrideOpen, setOverrideOpen] = useState<string | null>(null);
  const [schemaInput, setSchemaInput] = useState<Record<string, string>>({});
  const [extracting, setExtracting] = useState<string | null>(null);

  useEffect(() => {
    if (!companyId) return;
    setLoading(true);
    getClassifications(companyId)
      .then((res) => setItems(res.data || []))
      .catch((e) => setError(e?.message || 'Failed to load classifications'))
      .finally(() => setLoading(false));
  }, [companyId]);

  const handleApprove = async (id: string) => {
    try {
      await updateClassification(id, { human_approved: true });
      setItems((prev) =>
        prev.map((it) => (it.id === id ? { ...it, human_approved: true } : it))
      );
    } catch (e: any) {
      setError(e?.message || 'Approve failed');
    }
  };

  const handleOverride = async (id: string, newType: string) => {
    try {
      await updateClassification(id, { human_approved: true, human_type_override: newType });
      setItems((prev) =>
        prev.map((it) =>
          it.id === id ? { ...it, human_approved: true, human_type_override: newType } : it
        )
      );
      setOverrideOpen(null);
    } catch (e: any) {
      setError(e?.message || 'Override failed');
    }
  };

  const handleExtract = async (id: string) => {
    const raw = schemaInput[id] || '';
    const fields = raw.split(',').map((f) => f.trim()).filter(Boolean);
    if (!fields.length) return;
    setExtracting(id);
    try {
      const res = await extractSchema(id, fields);
      setItems((prev) =>
        prev.map((it) =>
          it.id === id ? { ...it, extracted_fields: res.data?.extracted_fields || it.extracted_fields } : it
        )
      );
    } catch (e: any) {
      setError(e?.message || 'Extraction failed');
    } finally {
      setExtracting(null);
    }
  };

  const allReviewed = items.length > 0 && items.every((it) => it.human_approved !== null);

  if (!companyId) {
    return (
      <div className="min-h-screen bg-ob-bg flex items-center justify-center">
        <p className="text-ob-muted text-[13px]">No company selected. Start a new assessment.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-ob-bg pt-[60px] px-4 pb-10">
      <div className="max-w-[800px] mx-auto">
        <p className="font-mono text-[10px] text-ob-muted tracking-[0.12em] uppercase">
          Document Classification Review
        </p>
        <h1 className="font-display text-[24px] text-ob-text mt-1">
          Verify Auto-Classifications
        </h1>
        <p className="text-[12px] text-ob-muted mt-1">
          Review each document&apos;s auto-detected type. Approve or override before proceeding.
        </p>

        {error && (
          <div className="mt-4 text-[12px] text-red-400 bg-red-400/10 border border-red-400/20 rounded-[6px] px-3 py-2">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-ob-muted text-[13px] mt-6 animate-pulse">Loading classifications...</p>
        ) : items.length === 0 ? (
          <p className="text-ob-muted text-[13px] mt-6">No documents classified yet. Upload documents first.</p>
        ) : (
          <div className="mt-6 space-y-4">
            {items.map((item) => {
              const isApproved = item.human_approved === true;
              const displayType = item.human_type_override || item.auto_type;
              return (
                <div
                  key={item.id}
                  className={`bg-ob-glass border rounded-[12px] p-5 backdrop-blur-[28px] transition-all ${
                    isApproved ? 'border-ob-ok/40' : 'border-ob-edge'
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[13px] text-ob-text font-medium">
                          {displayType}
                        </span>
                        <span className="font-mono text-[11px] bg-ob-glass2 text-ob-muted px-1.5 py-0.5 rounded">
                          {(item.auto_confidence * 100).toFixed(0)}% conf
                        </span>
                        {isApproved && (
                          <span className="font-mono text-[10px] bg-ob-ok/20 text-ob-ok px-1.5 py-0.5 rounded">
                            ✓ Approved
                          </span>
                        )}
                        {item.human_type_override && (
                          <span className="font-mono text-[10px] bg-ob-warn/20 text-ob-warn px-1.5 py-0.5 rounded">
                            Overridden
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-ob-dim mt-1 font-mono">
                        Doc ID: {item.document_id.slice(0, 8)}…
                      </p>
                      {item.auto_reasoning && (
                        <p className="text-[11px] text-ob-muted mt-2 leading-relaxed">
                          {item.auto_reasoning}
                        </p>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 flex-shrink-0">
                      {!isApproved && (
                        <button
                          onClick={() => handleApprove(item.id)}
                          className="h-[32px] px-3 bg-ob-ok/20 text-ob-ok text-[11px] font-mono font-bold rounded-[6px] hover:bg-ob-ok/30 transition-all"
                        >
                          ✓ Approve
                        </button>
                      )}
                      <button
                        onClick={() => setOverrideOpen(overrideOpen === item.id ? null : item.id)}
                        className="h-[32px] px-3 bg-ob-glass2 border border-ob-edge text-ob-text text-[11px] font-mono rounded-[6px] hover:bg-ob-glass transition-all"
                      >
                        Override
                      </button>
                    </div>
                  </div>

                  {/* Override dropdown */}
                  {overrideOpen === item.id && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {DOC_TYPES.filter((t) => t !== item.auto_type).map((t) => (
                        <button
                          key={t}
                          onClick={() => handleOverride(item.id, t)}
                          className="px-2 py-1 text-[10px] font-mono bg-ob-glass2 border border-ob-edge text-ob-muted rounded hover:text-ob-text hover:border-ob-text/40 transition-all"
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Extracted fields */}
                  {item.extracted_fields && Object.keys(item.extracted_fields).length > 0 && (
                    <div className="mt-3 bg-ob-glass2 border border-ob-edge rounded-[8px] p-3">
                      <p className="font-mono text-[9px] text-ob-dim uppercase tracking-[0.12em] mb-2">
                        Extracted Fields
                      </p>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
                        {Object.entries(item.extracted_fields).map(([k, v]) => (
                          <div key={k} className="flex gap-2">
                            <span className="text-ob-muted font-mono">{k}:</span>
                            <span className="text-ob-text truncate">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Schema builder */}
                  <div className="mt-3 flex gap-2">
                    <input
                      className="flex-1 h-[32px] px-2 bg-ob-glass2 border border-ob-edge rounded-[6px] text-ob-text text-[11px] font-mono placeholder:text-ob-muted/50 focus:outline-none focus:ring-1 focus:ring-ob-text/30"
                      placeholder="Custom fields: revenue_crore, dscr, ..."
                      value={schemaInput[item.id] || ''}
                      onChange={(e) => setSchemaInput({ ...schemaInput, [item.id]: e.target.value })}
                    />
                    <button
                      onClick={() => handleExtract(item.id)}
                      disabled={extracting === item.id || !schemaInput[item.id]?.trim()}
                      className="h-[32px] px-3 bg-ob-glass2 border border-ob-edge text-ob-text text-[11px] font-mono rounded-[6px] hover:bg-ob-glass disabled:opacity-40 transition-all"
                    >
                      {extracting === item.id ? 'Extracting…' : 'Re-extract'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Continue */}
        <div className="mt-8 flex justify-between items-center">
          <p className="text-[11px] text-ob-muted">
            {allReviewed
              ? '✓ All documents reviewed'
              : `${items.filter((i) => i.human_approved !== null).length} / ${items.length} reviewed`}
          </p>
          <button
            onClick={() => router.push('/app/notes')}
            disabled={!allReviewed}
            className="h-[44px] px-6 bg-ob-text text-ob-bg text-[13px] font-bold rounded-[6px] hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition-opacity"
          >
            Continue to Analysis →
          </button>
        </div>
      </div>
    </div>
  );
}
