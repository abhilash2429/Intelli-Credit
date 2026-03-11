'use client';

import './globals.css';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

const MARKETING_LINKS = [
  { href: '/', label: 'Home' },
  { href: '/about', label: 'About' },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAppRoute = pathname.startsWith('/app');
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <html lang="en">
      <head>
        <title>IntelliCredit | AI Credit Appraisal</title>
        <meta name="description" content="AI-powered Credit Appraisal Engine for Indian Corporate Lending" />
      </head>
      <body className="bg-ob-bg text-ob-text antialiased">
        {!isAppRoute && (
          <nav
            className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-[60px] py-[26px] transition-all duration-300"
            style={{
              backgroundColor: scrolled ? 'var(--ob-bg)' : 'transparent',
              backdropFilter: scrolled ? 'blur(28px)' : 'none',
              borderBottom: scrolled ? '1px solid var(--ob-edge)' : '1px solid transparent'
            }}
          >
            <Link href="/" className="font-display text-[20px] tracking-[0.01em] text-ob-text no-underline">
              Intelli<em className="not-italic italic opacity-55">Credit</em>
            </Link>

            <div className="flex gap-[36px]">
              {MARKETING_LINKS.map((link) => {
                const isActive = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`text-[12px] font-normal tracking-[0.05em] no-underline transition-colors ${isActive ? 'text-ob-text' : 'text-ob-muted hover:text-ob-text'
                      }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </div>

            <Link
              href="/app/start"
              className="text-[12px] font-medium tracking-[0.03em] text-ob-text bg-ob-glass border border-ob-edge px-[22px] py-[9px] rounded-full backdrop-blur-[20px] transition-all duration-200 hover:bg-ob-glass2 hover:border-ob-edge2 no-underline"
            >
              Get Started →
            </Link>
          </nav>
        )}

        <main>{children}</main>
      </body>
    </html>
  );
}
