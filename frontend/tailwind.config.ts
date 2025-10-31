import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}', './lib/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        night: '#030712',
        holo: {
          100: '#7dd3fc',
          200: '#38bdf8',
          300: '#0ea5e9',
          400: '#0284c7',
          500: '#0f172a'
        },
        neon: {
          blue: '#38bdf8',
          cyan: '#67e8f9',
          indigo: '#818cf8'
        }
      },
      fontFamily: {
        display: ['"Rajdhani"', 'sans-serif'],
        mono: ['"Share Tech Mono"', 'monospace'],
        sans: ['"Exo 2"', 'sans-serif']
      },
      boxShadow: {
        holo: '0 0 30px rgba(56, 189, 248, 0.25)',
        inset: 'inset 0 0 25px rgba(14, 165, 233, 0.45)'
      },
      animation: {
        pulseGlow: 'pulseGlow 6s ease-in-out infinite',
        fadeInUp: 'fadeInUp 0.6s ease-out forwards'
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { opacity: 0.6 },
          '50%': { opacity: 1 }
        },
        fadeInUp: {
          '0%': { opacity: 0, transform: 'translateY(12px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' }
        }
      }
    }
  },
  plugins: []
};

export default config;
