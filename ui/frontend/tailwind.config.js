/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        burgundy: {
          DEFAULT: 'var(--color-burgundy)',
          deep: 'var(--color-burgundy-deep)',
        },
        gold: {
          DEFAULT: 'var(--color-gold)',
          soft: 'var(--color-gold-soft)',
        },
        ink: 'var(--color-ink)',
        paper: 'var(--color-paper)',
        line: 'var(--color-line)',
        muted: 'var(--color-muted)',
        positive: 'var(--color-positive)',
        negative: 'var(--color-negative)',
      },
      fontFamily: {
        serif: ['var(--font-serif)', 'Georgia', 'serif'],
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
      },
      spacing: {
        xs: 'var(--space-xs)',
        sm: 'var(--space-sm)',
        md: 'var(--space-md)',
        lg: 'var(--space-lg)',
        xl: 'var(--space-xl)',
        '2xl': 'var(--space-2xl)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
      },
    },
  },
  plugins: [],
}
