'use client';

import { useState, useRef, useEffect } from 'react';
import { chatWithCamV1 } from '@/lib/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
}

interface ChatInterfaceProps {
  companyId: string;
  companyName: string;
}

const STARTER_QUESTIONS = [
  'What are the key risk factors for this company?',
  'Summarize the financial health in 3 bullet points.',
  'Are there any litigation red flags?',
  'What is the recommended loan structure?',
  'Explain the DSCR and debt-to-equity situation.',
];

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export default function ChatInterface({ companyId, companyName }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;
    if (!UUID_REGEX.test(companyId)) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'This appraisal session is invalid or expired. Please run analysis again from Upload.' },
      ]);
      return;
    }

    const userMsg: Message = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await chatWithCamV1(companyId, text);
      const assistantMsg: Message = {
        role: 'assistant',
        content: response?.response || 'No response available for this question yet.',
        sources: response.sources,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const detail =
        err?.response?.data?.data?.message ||
        err?.response?.data?.detail ||
        err?.message ||
        'Please try again.';
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Sorry, I encountered an error. ${detail}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col flex-1">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 px-6 py-4">
        {messages.length === 0 && (
          <div className="text-center mt-8">
            <p className="text-ob-muted mb-6 text-[14px]">Ask anything about {companyName}&apos;s credit appraisal</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {STARTER_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  onClick={() => sendMessage(q)}
                  className="px-3 py-2 text-[12px] bg-ob-glass2 border border-ob-edge rounded-[12px] text-ob-text hover:bg-ob-glass2 hover:border-ob-text/30 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-2xl px-4 py-3 ${msg.role === 'user'
                  ? 'bg-ob-text text-ob-bg rounded-[12px] rounded-br-[2px]'
                  : 'bg-ob-glass2 text-ob-text rounded-[12px] rounded-bl-[2px]'
                }`}
            >
              <p className="text-[14px] whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {msg.sources.map((s, j) => (
                    <span
                      key={j}
                      className="px-2 py-0.5 text-[10px] rounded bg-ob-glass2 text-ob-text border border-ob-text/20"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-ob-glass2 rounded-[12px] rounded-bl-[2px] px-4 py-3">
              <p className="text-ob-muted text-[14px] animate-pulse">Thinking...</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-ob-edge bg-ob-glass p-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage(input)}
            placeholder="Ask about this credit appraisal..."
            className="flex-1 px-4 py-3 bg-ob-glass border border-ob-edge rounded-[12px] text-ob-text text-[14px] placeholder:text-ob-muted focus:outline-none focus:ring-2 focus:ring-ob-text/40"
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || loading}
            className="px-5 py-3 bg-ob-text text-ob-bg rounded-[12px] font-bold transition-colors hover:bg-ob-cream disabled:opacity-40 disabled:cursor-not-allowed"
          >
            →
          </button>
        </div>
      </div>
    </div>
  );
}
