/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"DM Serif Display"', 'Georgia', 'serif'],
        sans: ['"Inter Tight"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      colors: {
        brand: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        market: {
          DEFAULT: '#f0f7ff',
          50: '#f0f7ff',
          100: '#e0f0ff',
          200: '#c8e2ff',
          300: '#a6c8ff',
          400: '#7aa8f5',
          500: '#4a85e0',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#172554',
        },
        financial: {
          bg: '#f0f7ff',
          surface: '#ffffff',
          card: '#ffffff',
          border: '#d4e4fa',
          'border-light': '#b8d6f5',
          text: '#0f172a',
          'text-secondary': '#475569',
          'text-muted': '#94a3b8',
        },
        agent: {
          market: '#38bdf8',       // sky-400 - Market Analyst
          sentiment: '#a78bfa',    // violet-400 - Sentiment Analyst
          news: '#34d399',         // emerald-400 - News Analyst
          fundamentals: '#f472b6', // pink-400 - Fundamentals Analyst
          research: '#fb923c',     // orange-400 - Research
          trader: '#fbbf24',       // amber-400 - Trader
          risk: '#ef4444',         // red-500 - Risk
        },
        signal: {
          buy: '#059669',
          sell: '#dc2626',
          hold: '#d97706',
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'noise': "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E\")",
      },
      animation: {
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
        'slide-up': 'slideUp 0.3s ease-out',
        'fade-in': 'fadeIn 0.3s ease-out',
        'data-flow': 'dataFlow 2s linear infinite',
        'gradient-shift': 'gradientShift 6s ease infinite',
        'breathing': 'breathing 3s ease-in-out infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 8px rgba(56, 189, 248, 0.3)' },
          '50%': { boxShadow: '0 0 20px rgba(56, 189, 248, 0.6)' },
        },
        slideUp: {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        dataFlow: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        breathing: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
    },
  },
  plugins: [],
};
