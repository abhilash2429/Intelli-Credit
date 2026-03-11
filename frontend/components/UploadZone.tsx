'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

interface UploadedFile {
  file: File;
  type?: string;
}

interface UploadZoneProps {
  onFilesReady: (files: File[]) => void;
}

export default function UploadZone({ onFilesReady }: UploadZoneProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const newFiles = acceptedFiles.map((file) => ({
        file,
        type: guessDocType(file.name),
      }));
      const all = [...uploadedFiles, ...newFiles];
      setUploadedFiles(all);
      onFilesReady(all.map((f) => f.file));
    },
    [uploadedFiles, onFilesReady]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/csv': ['.csv'],
      'application/json': ['.json'],
      'application/xml': ['.xml'],
      'text/xml': ['.xml'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
    },
    multiple: true,
  });

  const removeFile = (index: number) => {
    const updated = uploadedFiles.filter((_, i) => i !== index);
    setUploadedFiles(updated);
    onFilesReady(updated.map((f) => f.file));
  };

  return (
    <div>
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-[12px] p-10 text-center cursor-pointer transition-all duration-200 ${
          isDragActive
            ? 'border-ob-text bg-ob-glass2'
            : 'border-ob-edge bg-ob-glass2 hover:border-ob-text/50'
        }`}
      >
        <input {...getInputProps()} />
        <p className="text-ob-text text-[15px]">
          {isDragActive
            ? 'Drop files here...'
            : 'Drag & drop files, or click to browse'}
        </p>
        <p className="text-ob-muted text-[12px] mt-2">
          PDF, DOCX, CSV, XML, Excel, JPEG, PNG
        </p>
      </div>

      {uploadedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          {uploadedFiles.map((uf, i) => (
            <div
              key={i}
              className="flex items-center justify-between bg-ob-glass2 rounded-[12px] px-4 py-2.5 border border-ob-edge"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className="w-1.5 h-1.5 rounded-full bg-ob-ok flex-shrink-0" />
                <span className="font-mono text-[12px] text-ob-text truncate">
                  {uf.file.name}
                </span>
                {uf.type && (
                  <span className="px-2 py-0.5 text-[10px] rounded bg-ob-glass2 text-ob-text border border-ob-text/20 flex-shrink-0">
                    {uf.type}
                  </span>
                )}
              </div>
              <button
                onClick={() => removeFile(i)}
                className="text-ob-muted hover:text-ob-warn text-[12px] ml-2 flex-shrink-0"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function guessDocType(filename: string): string {
  const lower = filename.toLowerCase();
  if (lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.png')) return 'Scanned Image';
  if (lower.endsWith('.docx')) return 'Word Financial Document';
  if (lower.endsWith('.csv') || lower.endsWith('.xlsx') || lower.endsWith('.xls')) return 'Bank Statement';
  if (lower.endsWith('.xml')) return 'GST XML';
  if (lower.endsWith('.json') && lower.includes('itr')) return 'ITR JSON';
  if (lower.includes('gst') || lower.includes('gstr')) return 'GSTR-3B';
  if (lower.includes('bank') || lower.includes('statement')) return 'Bank Statement';
  if (lower.includes('annual') || lower.includes('report')) return 'Annual Report';
  if (lower.includes('audit')) return 'Audit Report';
  if (lower.includes('itr') || lower.includes('tax')) return 'ITR';
  if (lower.includes('balancesheet') || lower.includes('balance')) return 'Balance Sheet';
  return 'Document';
}
