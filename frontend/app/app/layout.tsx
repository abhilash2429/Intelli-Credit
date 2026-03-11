'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAnalysisStore } from '@/store/analysisStore';

const LINEAR_STEPS = [
  { step: 0, href: '/app/upload', label: 'Upload' },
  { step: 1, href: '/app/notes', label: 'Notes' },
  { step: 2, href: '/app/pipeline', label: 'Pipeline' },
  { step: 3, href: '/app/results', label: 'Results' },
];

const OUTPUT_TABS = [
  { href: '/app/score', label: 'Score' },
  { href: '/app/results', label: 'Results' },
  { href: '/app/explain', label: 'Explain' },
  { href: '/app/chat', label: 'Chat' },
  { href: '/app/cam', label: 'CAM' },
];

// Map routes to their required step
const ROUTE_STEP_MAP: Record<string, number> = {
  '/app/upload': 0,
  '/app/notes': 1,
  '/app/pipeline': 2,
  '/app/score': 3,
  '/app/results': 3,
  '/app/explain': 3,
  '/app/chat': 3,
  '/app/cam': 3,
};

export default function AppShellLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { companyName, pipelineStep, canAccess, reset, _hasHydrated } = useAnalysisStore();

  const isStartPage = pathname === '/app/start';
  const isOutputPage = pipelineStep >= 3 && (ROUTE_STEP_MAP[pathname] === 3);

  // Hydration RouteGuard Wait Block
  if (!_hasHydrated) {
    return (
      <div className="min-h-screen bg-ob-bg flex flex-col items-center justify-center space-y-4">
        <div className="w-6 h-6 border-2 border-ob-dim border-t-ob-text rounded-full animate-spin" />
        <p className="font-mono text-[10px] text-ob-muted tracking-[0.14em] uppercase animate-pulse">Initializing Pipeline...</p>
      </div>
    );
  }

  // RouteGuard Enforcement Logic
  if (!isStartPage) {
    const requiredStep = ROUTE_STEP_MAP[pathname];
    if (requiredStep !== undefined && !canAccess(requiredStep)) {
      const accessible = LINEAR_STEPS.filter((s) => canAccess(s.step));
      const target = accessible.length > 0 ? accessible[accessible.length - 1].href : '/app/start';
      // Force redirect outside of rendering children to block UI flashes
      if (typeof window !== 'undefined') {
        router.replace(target);
        return null; // Block render pipeline strictly
      }
    }
  }

  // Don't render app shell for the /app/start page
  if (isStartPage) {
    return <>{children}</>;
  }

  const handleNewAssessment = () => {
    reset();
    router.push('/app/start');
  };

  return (
    <div className="min-h-screen bg-ob-bg">
      {/* App Shell Navbar */}
      <nav className="sticky top-0 z-50 h-14 bg-ob-surface border-b border-ob-edge flex items-center px-6">
        {/* Logo */}
        <Link href="/" className="font-display text-[20px] tracking-[0.01em] text-ob-text no-underline flex items-center shrink-0">
          Intelli<em className="not-italic italic opacity-55">Credit</em>
        </Link>

        {/* Centre: Step indicator or Output tabs */}
        <div className="flex-1 flex items-center justify-center gap-2">
          {isOutputPage ? (
            /* Output tab bar */
            <div className="flex items-center gap-5">
              {OUTPUT_TABS.map((tab) => {
                const isActive = pathname === tab.href;
                return (
                  <Link
                    key={tab.href}
                    href={tab.href}
                    className={`text-[13px] font-medium no-underline pb-0.5 transition-colors ${isActive
                      ? 'text-ob-text border-b-2 border-ob-text'
                      : 'text-ob-muted hover:text-ob-text'
                      }`}
                  >
                    {tab.label}
                  </Link>
                );
              })}
            </div>
          ) : (
            /* Linear step indicator */
            <div className="flex items-center gap-1">
              {LINEAR_STEPS.map((s, idx) => {
                const isCompleted = pipelineStep > s.step;
                const isCurrent = pathname === s.href;
                const isAccessible = canAccess(s.step);
                const isLocked = !isAccessible;

                return (
                  <div key={s.href} className="flex items-center">
                    {/* Step circle + label */}
                    {isLocked ? (
                      <div className="flex items-center gap-1.5 cursor-not-allowed">
                        <div className="w-5 h-5 rounded-full border border-ob-edge flex items-center justify-center">
                          <span className="text-[9px] font-mono text-ob-muted">{idx + 1}</span>
                        </div>
                        <span className="text-[12px] text-ob-muted">{s.label}</span>
                      </div>
                    ) : (
                      <Link href={s.href} className="flex items-center gap-1.5 no-underline">
                        <div
                          className={`w-5 h-5 rounded-full flex items-center justify-center ${isCompleted
                            ? 'bg-ob-text'
                            : isCurrent
                              ? 'border-2 border-ob-text'
                              : 'border border-ob-edge'
                            }`}
                        >
                          {isCompleted ? (
                            <svg className="w-3 h-3 text-ob-bg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="20 6 9 17 4 12" />
                            </svg>
                          ) : (
                            <span className={`text-[9px] font-mono ${isCurrent ? 'text-ob-text' : 'text-ob-muted'}`}>{idx + 1}</span>
                          )}
                        </div>
                        <span className={`text-[12px] ${isCurrent ? 'text-ob-text font-medium' : isCompleted ? 'text-ob-text' : 'text-ob-muted'}`}>
                          {s.label}
                        </span>
                      </Link>
                    )}

                    {/* Connector line */}
                    {idx < LINEAR_STEPS.length - 1 && (
                      <div className={`w-6 h-px mx-2 ${pipelineStep > s.step ? 'bg-ob-text' : 'bg-ob-edge'}`} />
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right side */}
        <div className="flex items-center gap-4 shrink-0">
          {isOutputPage && (
            <button
              onClick={handleNewAssessment}
              className="px-4 py-1.5 bg-ob-glass border border-ob-edge text-ob-text rounded-[100px] text-[12px] font-medium hover:bg-ob-glass2 hover:border-ob-edge2 transition-all transition-[backdrop-filter] backdrop-blur-[20px]"
            >
              + New Assessment
            </button>
          )}
          <span className="font-mono text-[12px] text-ob-muted truncate max-w-[180px]">
            {companyName ? `Assessing: ${companyName}` : ''}
          </span>
        </div>
      </nav>

      {/* Page content */}
      <div className="min-h-[calc(100vh-56px)]">
        {children}
      </div>
    </div>
  );
}
