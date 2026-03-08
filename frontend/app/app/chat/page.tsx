'use client';

import { useAnalysisStore } from '@/store/analysisStore';
import ChatInterface from '@/components/ChatInterface';

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export default function ChatPage() {
  const { companyId, companyName, uploadedFileNames } = useAnalysisStore();
  const isValidSession = UUID_REGEX.test(companyId);

  return (
    <div className="bg-ic-page h-[calc(100vh-56px)] flex">
      {/* Left pane — 30% document context */}
      <aside className="w-[30%] bg-ic-surface border-r border-ic-border flex flex-col overflow-y-auto p-5 hidden lg:flex">
        <p className="text-[10px] font-medium tracking-[0.12em] uppercase text-ic-muted mb-3">Documents in Context</p>
        {uploadedFileNames.length > 0 ? (
          <div className="space-y-1.5">
            {uploadedFileNames.map((name, i) => (
              <div key={i} className="flex items-center gap-2 py-2 border-b border-ic-border last:border-0">
                <span className="w-1.5 h-1.5 rounded-full bg-ic-positive flex-shrink-0" />
                <span className="font-mono text-[12px] text-ic-text truncate">{name}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[12px] text-ic-muted">No documents uploaded yet.</p>
        )}
      </aside>

      {/* Right pane — 70% chat */}
      <div className="flex-1 flex flex-col">
        {/* Chat header */}
        <div className="px-6 py-3 border-b border-ic-border bg-ic-surface flex items-center justify-between">
          <div>
            <p className="text-[14px] font-medium text-ic-text">{companyName || 'Company'}</p>
            <p className="text-[11px] text-ic-muted">Powered by RAG</p>
          </div>
        </div>

        {/* Chat area */}
        {companyId && isValidSession ? (
          <ChatInterface companyId={companyId} companyName={companyName || 'Company'} />
        ) : (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="bg-[#fdf0e8] border border-[#f3d5bc] rounded-[10px] p-5 max-w-md">
              <p className="text-ic-warning text-[13px]">No valid appraisal session found. Please run analysis from Upload first.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
