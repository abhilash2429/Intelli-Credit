'use client';

import ReactMarkdown from 'react-markdown';

interface CamPreviewProps {
  camText: string;
}

export default function CamPreview({ camText }: CamPreviewProps) {
  return (
    <div className="prose max-w-none prose-headings:font-display prose-headings:text-ob-text prose-h1:text-[22px] prose-h2:text-[16px] prose-p:text-ob-text prose-p:text-[14px] prose-p:leading-[1.75] prose-li:text-ob-text prose-li:text-[14px] prose-strong:text-ob-text prose-a:text-ob-text prose-a:no-underline hover:prose-a:underline prose-table:border-ob-edge prose-th:bg-ob-glass2 prose-th:text-ob-text prose-td:border-ob-edge prose-td:font-mono prose-td:text-[13px]">
      <ReactMarkdown>{camText}</ReactMarkdown>
    </div>
  );
}
