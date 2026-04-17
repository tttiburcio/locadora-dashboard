/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // B&W palette mapped to zinc — all existing g-* classes now render monochrome
        g: {
          950: '#09090b',  // zinc-950
          900: '#18181b',  // zinc-900
          850: '#1e1e21',
          800: '#27272a',  // zinc-800
          750: '#303034',
          700: '#3f3f46',  // zinc-700
          600: '#52525b',  // zinc-600
          500: '#71717a',  // zinc-500
          400: '#a1a1aa',  // zinc-400
          300: '#d4d4d8',  // zinc-300
          200: '#e4e4e7',  // zinc-200
          100: '#f4f4f5',  // zinc-100
          50:  '#fafafa',  // zinc-50
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
