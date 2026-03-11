import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'ob-bg': 'var(--ob-bg)',
        'ob-surface': 'var(--ob-surface)',
        'ob-surface2': 'var(--ob-surface2)',
        'ob-glass': 'var(--ob-glass)',
        'ob-glass2': 'var(--ob-glass2)',
        'ob-edge': 'var(--ob-edge)',
        'ob-edge2': 'var(--ob-edge2)',
        'ob-text': 'var(--ob-text)',
        'ob-muted': 'var(--ob-muted)',
        'ob-dim': 'var(--ob-dim)',
        'ob-cream': 'var(--ob-cream)',
        'ob-warn': 'var(--ob-warn)',
        'ob-warn-bg': 'var(--ob-warn-bg)',
        'ob-warn-edge': 'var(--ob-warn-edge)',
        'ob-ok': 'var(--ob-ok)',
        'ob-ok-bg': 'var(--ob-ok-bg)',
        'ob-ok-edge': 'var(--ob-ok-edge)',
      },
      fontFamily: {
        display: ['DM Serif Display', 'serif'],
        body: ['Manrope', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
};

export default config;
