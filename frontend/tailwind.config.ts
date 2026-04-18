import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        sparq: {
          lime: '#c8ff00',
          'lime-dark': '#a8d600',
          'lime-light': '#d4ff33',
          'lime-glow': 'rgba(200,255,0,0.18)',
          charcoal: '#0a0a0a',
          'charcoal-light': '#141414',
          dark: '#050505',
          ink: '#0c0c0c',
          fog: '#1a1a1a',
        },
      },
      fontFamily: {
        display: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'display-xl': ['clamp(3rem, 7vw, 6.5rem)', { lineHeight: '0.95', letterSpacing: '-0.03em' }],
        'display-lg': ['clamp(2.25rem, 5vw, 4.5rem)', { lineHeight: '1.0', letterSpacing: '-0.025em' }],
        'display-md': ['clamp(1.75rem, 3.5vw, 3rem)', { lineHeight: '1.05', letterSpacing: '-0.02em' }],
        eyebrow: ['0.72rem', { letterSpacing: '0.22em', lineHeight: '1' }],
      },
      boxShadow: {
        'lime-glow': '0 0 80px -20px rgba(200,255,0,0.45)',
        'lime-glow-sm': '0 0 40px -16px rgba(200,255,0,0.35)',
        card: '0 1px 0 0 rgba(255,255,255,0.04) inset, 0 30px 60px -30px rgba(0,0,0,0.6)',
      },
      backgroundImage: {
        'lime-conic':
          'conic-gradient(from calc(var(--angle, 0deg)) at 50% 50%, rgba(200,255,0,0) 0deg, rgba(200,255,0,0.55) 90deg, rgba(200,255,0,0) 180deg, rgba(200,255,0,0.55) 270deg, rgba(200,255,0,0) 360deg)',
        'soft-radial':
          'radial-gradient(ellipse at top, rgba(200,255,0,0.08), transparent 60%)',
      },
      keyframes: {
        slideIn: {
          '0%': { opacity: '0', transform: 'translateY(-8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'thinking-progress': {
          '0%': { width: '0%', marginLeft: '0%' },
          '50%': { width: '60%', marginLeft: '20%' },
          '100%': { width: '0%', marginLeft: '100%' },
        },
        'aura-pulse': {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.65' },
        },
        'border-spin': {
          '0%': { '--angle': '0deg' },
          '100%': { '--angle': '360deg' },
        },
        marquee: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        blink: {
          '0%, 49%': { opacity: '1' },
          '50%, 100%': { opacity: '0' },
        },
      },
      animation: {
        slideIn: 'slideIn 0.3s ease-out forwards',
        'thinking-progress': 'thinking-progress 2s ease-in-out infinite',
        'aura-pulse': 'aura-pulse 4s ease-in-out infinite',
        'border-spin': 'border-spin 8s linear infinite',
        marquee: 'marquee 30s linear infinite',
        blink: 'blink 1s step-end infinite',
      },
    },
  },
  plugins: [],
}
export default config
