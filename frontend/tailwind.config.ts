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
          lime: '#CDDC39',
          'lime-dark': '#B0BF1A',
          'lime-light': '#D4E157',
          charcoal: '#1a1a2e',
          'charcoal-light': '#2d2d3d',
          dark: '#16213e',
        }
      }
    },
  },
  plugins: [],
}
export default config
