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
          charcoal: '#0a0a0a',
          'charcoal-light': '#141414',
          dark: '#050505',
        }
      },
      fontFamily: {
        display: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
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
      },
      animation: {
        slideIn: 'slideIn 0.3s ease-out forwards',
        'thinking-progress': 'thinking-progress 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
export default config
