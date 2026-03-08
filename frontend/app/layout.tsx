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
      <body className="bg-ic-page text-ic-text antialiased">
        {/* Liquid Glass Navbar — only shown on marketing routes */}
        {!isAppRoute && (
          <nav
            className="fixed top-0 left-0 right-0 z-50 h-[60px] flex items-center px-8 transition-all duration-300"
            style={{
              backgroundColor: scrolled ? 'rgba(250, 248, 243, 0.82)' : 'rgba(250, 248, 243, 0.55)',
              backdropFilter: 'blur(18px) saturate(180%)',
              WebkitBackdropFilter: 'blur(18px) saturate(180%)',
              borderBottom: '1px solid rgba(230, 225, 214, 0.5)',
              boxShadow: '0 1px 0 rgba(44, 74, 46, 0.06), 0 4px 24px rgba(44, 74, 46, 0.04)',
            }}
          >
            {/* Logo */}
            <Link href="/" className="flex items-center gap-0.5 shrink-0 no-underline">
              <span className="font-display text-lg font-normal text-ic-text">Intelli</span>
              <span className="font-display text-lg italic text-ic-accent">Credit</span>
            </Link>

            {/* Centre nav links */}
            <div className="flex-1 flex items-center justify-center gap-8">
              {MARKETING_LINKS.map((link) => {
                const isActive = pathname === link.href;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`text-[13px] font-medium no-underline transition-colors ${
                      isActive
                        ? 'text-ic-accent underline underline-offset-4 decoration-2 decoration-ic-accent'
                        : 'text-ic-muted hover:text-ic-accent'
                    }`}
                  >
                    {link.label}
                  </Link>
                );
              })}
            </div>

            {/* CTA pill */}
            <Link
              href="/app/start"
              className="shrink-0 px-5 py-[7px] border border-ic-accent text-ic-accent text-[13px] font-medium rounded-full no-underline transition-all duration-200 hover:bg-ic-accent hover:text-white"
            >
              Get Started →
            </Link>
          </nav>
        )}

        {/* Page content */}
        <main>{children}</main>
      </body>
    </html>
  );
}
