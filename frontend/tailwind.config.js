/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Space Grotesk', 'Noto Sans SC', 'PingFang SC', 'Segoe UI', 'sans-serif'],
        mono: ['IBM Plex Mono', 'SFMono-Regular', 'Consolas', 'monospace'],
      },
      colors: {
        primary: {
          50: '#f4fbff',
          100: '#dcf5ff',
          200: '#b8ebff',
          300: '#7fdcff',
          400: '#3fc8ff',
          500: '#16a8f5',
          600: '#0b88d1',
          700: '#0b6aa5',
          800: '#0e4f7c',
          900: '#103f61',
        },
        slatex: {
          900: '#0b1420',
          800: '#121d2b',
          700: '#1f2d42',
          100: '#f3f7fb',
        },
        success: {
          100: '#dff8ea',
          500: '#18b26a',
          700: '#0f7b48',
        },
        warning: {
          100: '#fff3dc',
          500: '#f59b23',
          700: '#b56608',
        },
        danger: {
          100: '#ffe2e2',
          500: '#ee4f4f',
          700: '#a92929',
        },
      },
      boxShadow: {
        panel: '0 10px 32px rgba(17, 37, 63, 0.08)',
        panelHover: '0 16px 40px rgba(17, 37, 63, 0.14)',
      },
      animation: {
        'fade-in': 'fadeIn 220ms ease-out',
        'slide-up': 'slideUp 260ms ease-out',
        'pulse-soft': 'pulseSoft 1.8s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { transform: 'translateY(10px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '.65' },
        },
      },
    },
  },
  plugins: [],
}
