/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // CSS-variable driven palette — defined per theme in index.css
        g: {
          950: 'rgb(var(--g-950) / <alpha-value>)',
          900: 'rgb(var(--g-900) / <alpha-value>)',
          850: 'rgb(var(--g-850) / <alpha-value>)',
          800: 'rgb(var(--g-800) / <alpha-value>)',
          750: 'rgb(var(--g-750) / <alpha-value>)',
          700: 'rgb(var(--g-700) / <alpha-value>)',
          600: 'rgb(var(--g-600) / <alpha-value>)',
          500: 'rgb(var(--g-500) / <alpha-value>)',
          400: 'rgb(var(--g-400) / <alpha-value>)',
          300: 'rgb(var(--g-300) / <alpha-value>)',
          200: 'rgb(var(--g-200) / <alpha-value>)',
          100: 'rgb(var(--g-100) / <alpha-value>)',
          50:  'rgb(var(--g-50)  / <alpha-value>)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      keyframes: {
        fadeUp: {
          '0%':   { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideInRight: {
          '0%':   { opacity: '0', transform: 'translateX(100%)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        pageFade: {
          '0%':   { opacity: '0', transform: 'translateX(6px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '.4' },
        },
      },
      animation: {
        'fade-up':       'fadeUp 0.4s ease-out both',
        'fade-in':       'fadeIn 0.3s ease-out both',
        'slide-in-right':'slideInRight 0.32s cubic-bezier(0.32,0.72,0,1) both',
        'page-fade':     'pageFade 0.22s ease-out both',
        'pulse-slow':    'pulse 2s cubic-bezier(0.4,0,0.6,1) infinite',
      },
    },
  },
  plugins: [],
}
