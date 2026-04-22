import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './content/**/*.{mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--color-background)',
        surface: 'var(--color-surface)',
        border: 'var(--color-border)',
        'text-primary': 'var(--color-text-primary)',
        'text-muted': 'var(--color-text-muted)',
        accent: 'var(--color-accent)',
        'accent-hover': 'var(--color-accent-hover)',
        'code-bg': 'var(--color-code-bg)',
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'sans-serif'],
        mono: ['var(--font-jetbrains)', 'monospace'],
      },
    },
  },
  plugins: [],
}

export default config
