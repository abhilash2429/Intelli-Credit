'use client';

import { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';

pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

export default function DocumentViewer({ url }: { url: string }) {
  const [pages, setPages] = useState<number>(1);
  const [page, setPage] = useState(1);

  return (
    <div className="bg-ob-glass border border-ob-edge rounded-[12px] p-[20px] backdrop-blur-[28px]">
      <p className="font-mono text-[9px] font-normal tracking-[0.14em] uppercase text-ob-dim mb-2.5">Document Viewer</p>
      <div className="overflow-auto rounded-[12px] bg-ob-glass2 p-3">
        <Document file={url} onLoadSuccess={(d) => setPages(d.numPages)}>
          <Page pageNumber={page} width={620} />
        </Document>
      </div>
      <div className="mt-3 flex gap-3 items-center">
        <button
          disabled={page <= 1}
          onClick={() => setPage((p) => p - 1)}
          className="px-3 py-1 rounded-[6px] bg-ob-glass2 border border-ob-edge text-ob-text text-[12px] disabled:opacity-40"
        >
          Prev
        </button>
        <span className="text-ob-muted text-[12px] font-mono">
          {page} / {pages}
        </span>
        <button
          disabled={page >= pages}
          onClick={() => setPage((p) => p + 1)}
          className="px-3 py-1 rounded-[6px] bg-ob-glass2 border border-ob-edge text-ob-text text-[12px] disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
