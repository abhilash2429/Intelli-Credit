'use client';

import { signIn, useSession } from 'next-auth/react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect } from 'react';

export default function LoginPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get('next') || '/app/start';

  useEffect(() => {
    if (status === 'authenticated') {
      router.replace(next);
    }
  }, [status, next, router]);

  return (
    <div className="min-h-screen bg-ob-bg flex items-center justify-center px-6">
      <div className="max-w-[520px] w-full bg-ob-glass border border-ob-edge rounded-[16px] p-8 text-center backdrop-blur-[28px]">
        <h1 className="font-display text-[28px] text-ob-text">Welcome to IntelliCredit</h1>
        <p className="mt-2 text-[13px] text-ob-muted">
          Sign in with Google to start a new credit appraisal session.
        </p>

        <button
          onClick={() => signIn('google', { callbackUrl: next })}
          className="mt-6 w-full h-[46px] bg-ob-text text-ob-bg rounded-[8px] text-[13px] font-semibold hover:opacity-90 transition-opacity"
        >
          Continue with Google
        </button>

        {status === 'loading' && (
          <p className="mt-4 text-[11px] text-ob-muted font-mono uppercase tracking-[0.12em]">Checking session…</p>
        )}

        {session?.user?.email && (
          <p className="mt-4 text-[12px] text-ob-muted">Signed in as {session.user.email}</p>
        )}
      </div>
    </div>
  );
}
