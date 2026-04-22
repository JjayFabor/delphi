# Claudhaus Public Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public-facing Next.js static site in `site/` with a marketing landing page, documentation section, and API reference, deployed to Vercel.

**Architecture:** Standalone Next.js 14 (App Router) app in `site/` folder, separate from the existing `dashboard-ui/`. Fully static (`output: 'export'`), all content from MDX files at build time, no database reads.

**Tech Stack:** Next.js 14, Tailwind CSS, next-mdx-remote, gray-matter, next-themes, shiki, lucide-react, Pagefind (static search), Vitest (unit tests)

---

## File Map

```
site/
  app/
    layout.tsx                       Root layout (ThemeProvider, Nav, Footer)
    page.tsx                         Landing page (hero, comparison, features, how-it-works)
    globals.css                      CSS variable tokens + dot-grid helper
    docs/
      layout.tsx                     Docs shell (Sidebar)
      [[...slug]]/page.tsx           Dynamic MDX-driven docs pages
    api-reference/
      layout.tsx                     API reference shell (Sidebar)
      [[...slug]]/page.tsx           Dynamic MDX-driven API pages
  content/
    docs/                            MDX source for all docs pages
    api/                             MDX source for all API reference pages
  components/
    Nav.tsx                          Sticky top nav with Search, ThemeToggle, CTA
    Footer.tsx                       Footer with links
    Sidebar.tsx                      Collapsible docs sidebar (active-state aware)
    Toc.tsx                          In-page TOC with scroll-spy
    MdxComponents.tsx                Custom MDX renderers (prose, tables, code)
    ThemeToggle.tsx                  Dark/light toggle button
    Search.tsx                       Pagefind command palette (Cmd+K)
    Callout.tsx                      Note / Warning / Danger callout blocks
  lib/
    mdx.ts                           MDX file loader (gray-matter, heading extraction)
    nav.ts                           Ordered sidebar config for docs + API reference
  __tests__/
    mdx.test.ts                      Unit tests for mdx.ts
    nav.test.ts                      Unit tests for nav.ts
  next.config.mjs
  tailwind.config.ts
  tsconfig.json
  postcss.config.js
  package.json
  vitest.config.ts
  .gitignore
```

---

### Task 1: Project scaffold

**Files:**
- Create: `site/package.json`
- Create: `site/next.config.mjs`
- Create: `site/tailwind.config.ts`
- Create: `site/tsconfig.json`
- Create: `site/postcss.config.js`
- Create: `site/vitest.config.ts`
- Create: `site/.gitignore`

- [ ] **Step 1: Create the `site/` directory**

```bash
mkdir -p /home/jjay/JjayFiles/claude-command-center/site
cd /home/jjay/JjayFiles/claude-command-center/site
```

- [ ] **Step 2: Create `site/package.json`**

```json
{
  "name": "claudhaus-site",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "postbuild": "npx pagefind --site out --output-path public/pagefind",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "14.2.3",
    "react": "^18",
    "react-dom": "^18",
    "next-themes": "^0.3.4",
    "next-mdx-remote": "^5.0.0",
    "gray-matter": "^4.0.3",
    "lucide-react": "^0.378.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10.0.1",
    "eslint": "^8",
    "eslint-config-next": "14.2.3",
    "postcss": "^8",
    "tailwindcss": "^3.4.1",
    "typescript": "^5",
    "pagefind": "^1.1.0",
    "shiki": "^1.6.1",
    "vitest": "^1.6.0",
    "@vitejs/plugin-react": "^4.2.1",
    "@testing-library/react": "^15.0.0",
    "@testing-library/jest-dom": "^6.4.2"
  }
}
```

- [ ] **Step 3: Create `site/next.config.mjs`**

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
}

export default nextConfig
```

- [ ] **Step 4: Create `site/tailwind.config.ts`**

```ts
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
```

- [ ] **Step 5: Create `site/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 6: Create `site/postcss.config.js`**

```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 7: Create `site/vitest.config.ts`**

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'node',
    globals: true,
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, '.') },
  },
})
```

- [ ] **Step 8: Create `site/.gitignore`**

```
node_modules/
.next/
out/
public/pagefind/
*.tsbuildinfo
.env*.local
```

- [ ] **Step 9: Install dependencies**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm install
```

Expected: `node_modules/` created, no peer dependency errors.

- [ ] **Step 10: Create minimal `app/globals.css` and `app/layout.tsx` to verify build**

Create `site/app/globals.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

Create `site/app/layout.tsx`:
```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>
}
```

Create `site/app/page.tsx`:
```tsx
export default function HomePage() {
  return <main><h1>Claudhaus</h1></main>
}
```

- [ ] **Step 11: Verify build succeeds**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm run build 2>&1 | tail -10
```

Expected: `Export successful` or `✓ Generating static pages`. No TypeScript errors.

- [ ] **Step 12: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/
git commit -m "feat(site): scaffold Next.js 14 static site"
```

---

### Task 2: Design system

**Files:**
- Modify: `site/app/globals.css`

- [ ] **Step 1: Write full `site/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --color-background: #ffffff;
  --color-surface: #f8f8fc;
  --color-border: #e4e4ef;
  --color-text-primary: #0a0a0f;
  --color-text-muted: #6b6b8a;
  --color-accent: #5b4ee8;
  --color-accent-hover: #7c6af7;
  --color-code-bg: #f3f3fa;
}

.dark {
  --color-background: #0a0a0f;
  --color-surface: #111118;
  --color-border: #1e1e2e;
  --color-text-primary: #f0f0ff;
  --color-text-muted: #6b6b8a;
  --color-accent: #7c6af7;
  --color-accent-hover: #9b8dff;
  --color-code-bg: #0f0f1a;
}

* {
  border-color: var(--color-border);
}

body {
  background-color: var(--color-background);
  color: var(--color-text-primary);
}

.dot-grid {
  background-image: radial-gradient(circle, var(--color-border) 1px, transparent 1px);
  background-size: 24px 24px;
}
```

- [ ] **Step 2: Verify Tailwind picks up the tokens**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm run build 2>&1 | grep -E "error|warning|success" | head -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/app/globals.css
git commit -m "feat(site): design system — CSS variables and dot-grid"
```

---

### Task 3: ThemeToggle component

**Files:**
- Create: `site/components/ThemeToggle.tsx`

- [ ] **Step 1: Create `site/components/ThemeToggle.tsx`**

```tsx
'use client'
import { useTheme } from 'next-themes'
import { Sun, Moon } from 'lucide-react'
import { useEffect, useState } from 'react'

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => setMounted(true), [])

  if (!mounted) return <div className="w-9 h-9" />

  return (
    <button
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface transition-colors"
      aria-label="Toggle theme"
    >
      {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  )
}
```

- [ ] **Step 2: Verify no TypeScript errors**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npx tsc --noEmit 2>&1 | head -20
```

Expected: no output (no errors).

- [ ] **Step 3: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/components/ThemeToggle.tsx
git commit -m "feat(site): ThemeToggle component"
```

---

### Task 4: Nav component

**Files:**
- Create: `site/components/Nav.tsx`

- [ ] **Step 1: Create `site/components/Nav.tsx`**

```tsx
import Link from 'next/link'
import { Github } from 'lucide-react'
import ThemeToggle from './ThemeToggle'

export default function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="mx-auto max-w-7xl flex items-center justify-between h-14 px-6">
        <Link href="/" className="font-semibold text-text-primary tracking-tight text-sm">
          claudhaus
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm text-text-muted">
          <Link href="/docs" className="hover:text-text-primary transition-colors">
            Docs
          </Link>
          <Link href="/api-reference" className="hover:text-text-primary transition-colors">
            API Reference
          </Link>
          <a
            href="https://github.com/JjayFabor/claudhaus"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-text-primary transition-colors flex items-center gap-1.5"
          >
            <Github size={14} />
            GitHub
          </a>
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link
            href="/docs/introduction"
            className="px-4 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
          >
            Get Started
          </Link>
        </div>
      </div>
    </header>
  )
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/components/Nav.tsx
git commit -m "feat(site): Nav component"
```

---

### Task 5: Footer + Root layout

**Files:**
- Create: `site/components/Footer.tsx`
- Modify: `site/app/layout.tsx`

- [ ] **Step 1: Create `site/components/Footer.tsx`**

```tsx
import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="border-t border-border mt-24">
      <div className="mx-auto max-w-7xl px-6 py-12 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <p className="font-semibold text-text-primary tracking-tight text-sm">claudhaus</p>
          <p className="text-xs text-text-muted mt-1">Personal AI. Self-hosted.</p>
        </div>
        <nav className="flex flex-wrap items-center gap-6 text-sm text-text-muted">
          <Link href="/docs" className="hover:text-text-primary transition-colors">Docs</Link>
          <Link href="/api-reference" className="hover:text-text-primary transition-colors">API Reference</Link>
          <a
            href="https://github.com/JjayFabor/claudhaus"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-text-primary transition-colors"
          >
            GitHub
          </a>
          <a
            href="https://github.com/JjayFabor/claudhaus/blob/main/LICENSE"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-text-primary transition-colors"
          >
            License
          </a>
        </nav>
      </div>
      <div className="border-t border-border">
        <p className="text-center text-xs text-text-muted py-4">
          Independent open-source project. Not affiliated with Anthropic.
        </p>
      </div>
    </footer>
  )
}
```

- [ ] **Step 2: Rewrite `site/app/layout.tsx`**

```tsx
import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import { ThemeProvider } from 'next-themes'
import Nav from '@/components/Nav'
import Footer from '@/components/Footer'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })
const jetbrains = JetBrains_Mono({ subsets: ['latin'], variable: '--font-jetbrains' })

export const metadata: Metadata = {
  title: { default: 'Claudhaus', template: '%s | Claudhaus' },
  description: 'Your personal AI agent. Self-hosted. Claude-native.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrains.variable} font-sans`}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          <Nav />
          {children}
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 3: Verify build**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm run build 2>&1 | tail -5
```

Expected: `Export successful`.

- [ ] **Step 4: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/components/Footer.tsx site/app/layout.tsx
git commit -m "feat(site): Footer and root layout with ThemeProvider"
```

---

### Task 6: Landing page

**Files:**
- Modify: `site/app/page.tsx`

- [ ] **Step 1: Write `site/app/page.tsx`**

```tsx
import Link from 'next/link'
import { Database, Pencil, Plug, Bot, Clock, Wrench } from 'lucide-react'

const features = [
  { icon: Database, title: 'Persistent Memory',  desc: 'Remembers facts, preferences, and past context across every session.' },
  { icon: Pencil,   title: 'Teachable Skills',   desc: 'Teach new workflows just by chatting — no config files, no restarts.' },
  { icon: Plug,     title: 'MCP Connectors',     desc: 'Self-installing integrations: GitHub, HubSpot, Slack, and more.' },
  { icon: Bot,      title: 'Sub-agents',         desc: 'Spawn focused specialists with their own workspaces and tool sets.' },
  { icon: Clock,    title: 'Scheduler',           desc: 'Schedule recurring tasks — reports, reminders, status checks.' },
  { icon: Wrench,   title: 'Self-Improving',     desc: 'Main reads and edits its own source code, syntax-checks, and restarts.' },
]

const comparison = [
  { feature: 'Model',           claudhaus: 'Claude-native (Agent SDK)',       openclaw: 'Multi-provider' },
  { feature: 'Setup',           claudhaus: 'One Python file, chat-driven',    openclaw: 'Config files + dashboard' },
  { feature: 'Memory',          claudhaus: 'BM25 search over Markdown',       openclaw: 'None built-in' },
  { feature: 'Integrations',    claudhaus: 'Self-installing MCP connectors',  openclaw: 'Config-file plugins' },
  { feature: 'Skills',          claudhaus: 'Teachable via chat, hot-loaded',  openclaw: 'Static plugins' },
  { feature: 'Sub-agents',      claudhaus: 'Spawnable via chat',              openclaw: 'Not built-in' },
  { feature: 'Self-improvement', claudhaus: 'Edits its own source code',      openclaw: 'No' },
  { feature: 'Target',          claudhaus: 'One person, personal ops',        openclaw: 'Teams, multi-user' },
]

const steps = [
  { n: 1, title: 'Clone & configure',         desc: 'git clone the repo and run the setup wizard. Done in under 5 minutes.' },
  { n: 2, title: 'Connect your Telegram bot', desc: 'Create a bot via BotFather, paste the token. Your agent is live.' },
  { n: 3, title: 'Start chatting',            desc: 'Name it, define its role, connect tools, and teach it your workflows — all by chatting.' },
]

export default function HomePage() {
  return (
    <main>
      {/* Hero */}
      <section className="relative overflow-hidden dot-grid">
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-[600px] h-[600px] rounded-full bg-accent opacity-[0.06] blur-[120px]" />
        </div>
        <div className="relative mx-auto max-w-4xl px-6 py-28 text-center">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-text-primary leading-tight tracking-tight">
            Your personal AI agent.<br />Self-hosted. Claude-native.
          </h1>
          <p className="mt-6 text-lg md:text-xl text-text-muted max-w-2xl mx-auto leading-relaxed">
            Send a message from your phone. Get your own AI on the other end — shaped to your role,
            connected to your tools, and getting smarter every conversation.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/docs/introduction"
              className="w-full sm:w-auto px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium transition-colors text-center"
            >
              Get Started →
            </Link>
            <a
              href="https://github.com/JjayFabor/claudhaus"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto px-6 py-3 rounded-lg border border-border hover:border-accent text-text-primary font-medium transition-colors text-center"
            >
              View on GitHub
            </a>
          </div>
          <div className="mt-10 mx-auto max-w-lg text-left">
            <pre className="bg-surface border border-border rounded-lg px-5 py-4 text-sm font-mono text-text-muted overflow-x-auto">
              <code>{`git clone https://github.com/JjayFabor/claudhaus.git
cd claudhaus
python3 scripts/setup.py`}</code>
            </pre>
          </div>
        </div>
      </section>

      {/* Comparison */}
      <section className="mx-auto max-w-5xl px-6 py-24">
        <h2 className="text-2xl md:text-3xl font-bold text-center text-text-primary mb-12">
          How it compares
        </h2>
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface">
                <th className="px-5 py-3 text-left font-medium text-text-muted w-1/3" />
                <th className="px-5 py-3 text-left font-semibold text-accent">claudhaus</th>
                <th className="px-5 py-3 text-left font-medium text-text-muted">OpenClaw</th>
              </tr>
            </thead>
            <tbody>
              {comparison.map((row, i) => (
                <tr
                  key={row.feature}
                  className={`border-b border-border last:border-0 ${i % 2 !== 0 ? 'bg-surface/40' : ''}`}
                >
                  <td className="px-5 py-3 font-medium text-text-muted">{row.feature}</td>
                  <td className="px-5 py-3 text-text-primary">
                    <span className="text-accent mr-1.5">✓</span>{row.claudhaus}
                  </td>
                  <td className="px-5 py-3 text-text-muted">{row.openclaw}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Feature cards */}
      <section className="mx-auto max-w-5xl px-6 py-12">
        <h2 className="text-2xl md:text-3xl font-bold text-center text-text-primary mb-12">
          Everything you need
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map(({ icon: Icon, title, desc }) => (
            <div key={title} className="rounded-lg border border-border bg-surface p-6">
              <div className="w-8 h-8 rounded-md bg-accent/10 flex items-center justify-center mb-4">
                <Icon size={16} className="text-accent" />
              </div>
              <h3 className="font-semibold text-text-primary mb-1 text-sm">{title}</h3>
              <p className="text-sm text-text-muted leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-4xl px-6 py-24">
        <h2 className="text-2xl md:text-3xl font-bold text-center text-text-primary mb-16">
          How it works
        </h2>
        <div className="flex flex-col md:flex-row items-start gap-8 md:gap-4">
          {steps.map((step, i) => (
            <div key={step.n} className="flex-1 flex flex-col items-start gap-3">
              <div className="flex items-center gap-4 w-full">
                <span className="flex-shrink-0 w-8 h-8 rounded-full bg-accent text-white text-sm font-bold flex items-center justify-center">
                  {step.n}
                </span>
                {i < steps.length - 1 && (
                  <div className="hidden md:block flex-1 h-px bg-border" />
                )}
              </div>
              <h3 className="font-semibold text-text-primary text-sm">{step.title}</h3>
              <p className="text-sm text-text-muted leading-relaxed">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  )
}
```

- [ ] **Step 2: Build and verify**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm run build 2>&1 | tail -5
```

Expected: `Export successful`, `out/index.html` exists.

- [ ] **Step 3: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/app/page.tsx
git commit -m "feat(site): landing page — hero, comparison, features, how-it-works"
```

---

### Task 7: MDX infrastructure — lib functions + tests

**Files:**
- Create: `site/lib/mdx.ts`
- Create: `site/lib/nav.ts`
- Create: `site/__tests__/mdx.test.ts`
- Create: `site/__tests__/nav.test.ts`

- [ ] **Step 1: Write failing tests in `site/__tests__/nav.test.ts`**

```ts
import { describe, it, expect } from 'vitest'
import { docsNav, apiNav } from '@/lib/nav'

describe('docsNav', () => {
  it('is a non-empty array', () => {
    expect(Array.isArray(docsNav)).toBe(true)
    expect(docsNav.length).toBeGreaterThan(0)
  })

  it('every section has a title and items array', () => {
    for (const section of docsNav) {
      expect(typeof section.title).toBe('string')
      expect(Array.isArray(section.items)).toBe(true)
      expect(section.items.length).toBeGreaterThan(0)
    }
  })

  it('every item has a title and slug string', () => {
    for (const section of docsNav) {
      for (const item of section.items) {
        expect(typeof item.title).toBe('string')
        expect(typeof item.slug).toBe('string')
        expect(item.slug.length).toBeGreaterThan(0)
      }
    }
  })

  it('contains introduction slug', () => {
    const all = docsNav.flatMap(s => s.items.map(i => i.slug))
    expect(all).toContain('introduction')
  })
})

describe('apiNav', () => {
  it('is a non-empty array', () => {
    expect(Array.isArray(apiNav)).toBe(true)
    expect(apiNav.length).toBeGreaterThan(0)
  })

  it('contains overview slug', () => {
    const all = apiNav.flatMap(s => s.items.map(i => i.slug))
    expect(all).toContain('overview')
  })
})
```

- [ ] **Step 2: Run nav tests — expect failure**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm test -- nav 2>&1 | tail -10
```

Expected: FAIL — `Cannot find module '@/lib/nav'`

- [ ] **Step 3: Create `site/lib/nav.ts`**

```ts
export interface NavItem {
  title: string
  slug: string
}

export interface NavSection {
  title: string
  items: NavItem[]
}

export const docsNav: NavSection[] = [
  {
    title: 'Getting Started',
    items: [
      { title: 'Introduction',  slug: 'introduction' },
      { title: 'Prerequisites', slug: 'prerequisites' },
      { title: 'Quick Start',   slug: 'quick-start' },
      { title: 'Configuration', slug: 'configuration' },
    ],
  },
  {
    title: 'Core Concepts',
    items: [
      { title: 'Memory',      slug: 'memory' },
      { title: 'Skills',      slug: 'skills' },
      { title: 'Connectors',  slug: 'connectors' },
      { title: 'Sub-agents',  slug: 'sub-agents' },
      { title: 'Scheduler',   slug: 'scheduler' },
    ],
  },
  {
    title: 'Guides',
    items: [
      { title: 'Connecting Telegram',  slug: 'guides/connecting-telegram' },
      { title: 'Adding a Connector',   slug: 'guides/adding-a-connector' },
      { title: 'Writing a Skill',      slug: 'guides/writing-a-skill' },
      { title: 'WSL2 Setup',           slug: 'guides/wsl2-setup' },
      { title: 'Linux Setup',          slug: 'guides/linux-setup' },
      { title: 'macOS Setup',          slug: 'guides/macos-setup' },
      { title: 'Docker Setup',         slug: 'guides/docker-setup' },
    ],
  },
]

export const apiNav: NavSection[] = [
  {
    title: 'API Reference',
    items: [
      { title: 'Overview', slug: 'overview' },
    ],
  },
  {
    title: 'Tools',
    items: [
      { title: 'Bash',              slug: 'bash' },
      { title: 'Read / Write / Edit', slug: 'read-write-edit' },
      { title: 'Glob / Grep',       slug: 'glob-grep' },
    ],
  },
  {
    title: 'Scheduler Tools',
    items: [
      { title: 'scheduler_add',    slug: 'scheduler-add' },
      { title: 'scheduler_list',   slug: 'scheduler-list' },
      { title: 'scheduler_remove', slug: 'scheduler-remove' },
      { title: 'schedule_once',    slug: 'schedule-once' },
    ],
  },
  {
    title: 'Sub-agent Tools',
    items: [
      { title: 'subagent_list',   slug: 'subagent-list' },
      { title: 'subagent_create', slug: 'subagent-create' },
      { title: 'subagent_run',    slug: 'subagent-run' },
    ],
  },
  {
    title: 'Connector Tools',
    items: [
      { title: 'connector_info', slug: 'connector-info' },
      { title: 'connector_add',  slug: 'connector-add' },
    ],
  },
  {
    title: 'Shared Context',
    items: [
      { title: 'share',           slug: 'share' },
      { title: 'revoke',          slug: 'revoke' },
      { title: 'shared (pull)',   slug: 'shared-pull' },
    ],
  },
  {
    title: 'Learning Tools',
    items: [
      { title: 'learn',                              slug: 'learn' },
      { title: 'skill_list / read / write / delete', slug: 'skill-tools' },
    ],
  },
]
```

- [ ] **Step 4: Run nav tests — expect pass**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm test -- nav 2>&1 | tail -5
```

Expected: `✓ 5 tests passed`

- [ ] **Step 5: Write failing test in `site/__tests__/mdx.test.ts`**

```ts
import { describe, it, expect } from 'vitest'
import path from 'path'
import { getAllSlugsFromDir, extractHeadings } from '@/lib/mdx'
import fs from 'fs'
import os from 'os'

describe('getAllSlugsFromDir', () => {
  it('returns slug arrays for MDX files in a directory', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mdx-test-'))
    fs.writeFileSync(path.join(tmp, 'introduction.mdx'), '# Intro')
    fs.mkdirSync(path.join(tmp, 'guides'))
    fs.writeFileSync(path.join(tmp, 'guides', 'quick-start.mdx'), '# Quick Start')

    const slugs = getAllSlugsFromDir(tmp)

    expect(slugs).toContainEqual(['introduction'])
    expect(slugs).toContainEqual(['guides', 'quick-start'])

    fs.rmSync(tmp, { recursive: true })
  })

  it('returns empty array for empty directory', () => {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mdx-empty-'))
    expect(getAllSlugsFromDir(tmp)).toEqual([])
    fs.rmSync(tmp, { recursive: true })
  })
})

describe('extractHeadings', () => {
  it('extracts h1, h2, h3 with ids', () => {
    const md = `# Getting Started\n\n## Prerequisites\n\n### Node.js setup`
    const headings = extractHeadings(md)
    expect(headings).toEqual([
      { id: 'getting-started', text: 'Getting Started', level: 1 },
      { id: 'prerequisites',   text: 'Prerequisites',   level: 2 },
      { id: 'nodejs-setup',    text: 'Node.js setup',   level: 3 },
    ])
  })

  it('handles empty content', () => {
    expect(extractHeadings('')).toEqual([])
  })
})
```

- [ ] **Step 6: Run mdx tests — expect failure**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm test -- mdx 2>&1 | tail -10
```

Expected: FAIL — `Cannot find module '@/lib/mdx'`

- [ ] **Step 7: Create `site/lib/mdx.ts`**

```ts
import fs from 'fs'
import path from 'path'
import matter from 'gray-matter'

const CONTENT_ROOT = path.join(process.cwd(), 'content')

export interface DocFrontmatter {
  title: string
  description: string
}

export interface Heading {
  id: string
  text: string
  level: number
}

export interface DocMeta {
  frontmatter: DocFrontmatter
  rawContent: string
  headings: Heading[]
}

export function extractHeadings(md: string): Heading[] {
  const re = /^(#{1,3})\s+(.+)$/gm
  const headings: Heading[] = []
  let match
  while ((match = re.exec(md)) !== null) {
    const level = match[1].length
    const text = match[2].trim()
    const id = text
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
    headings.push({ id, text, level })
  }
  return headings
}

export function getAllSlugsFromDir(dir: string): string[][] {
  const result: string[][] = []

  function walk(current: string, base: string) {
    const entries = fs.readdirSync(current, { withFileTypes: true })
    for (const entry of entries) {
      const full = path.join(current, entry.name)
      if (entry.isDirectory()) {
        walk(full, base)
      } else if (entry.name.endsWith('.mdx')) {
        const rel = path.relative(base, full).replace(/\.mdx$/, '')
        result.push(rel.split(path.sep))
      }
    }
  }

  walk(dir, dir)
  return result
}

export function getAllSlugs(section: 'docs' | 'api'): string[][] {
  const dir = path.join(CONTENT_ROOT, section)
  if (!fs.existsSync(dir)) return []
  return getAllSlugsFromDir(dir)
}

export function getDocMeta(section: 'docs' | 'api', slug: string[]): DocMeta | null {
  const filePath = path.join(CONTENT_ROOT, section, ...slug) + '.mdx'
  if (!fs.existsSync(filePath)) return null

  const raw = fs.readFileSync(filePath, 'utf-8')
  const { content, data } = matter(raw)

  return {
    frontmatter: data as DocFrontmatter,
    rawContent: content,
    headings: extractHeadings(content),
  }
}
```

- [ ] **Step 8: Run all tests — expect pass**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm test 2>&1 | tail -5
```

Expected: all tests pass (7 total).

- [ ] **Step 9: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/lib/ site/__tests__/
git commit -m "feat(site): MDX lib and nav config with passing tests"
```

---

### Task 8: MDX components

**Files:**
- Create: `site/components/Callout.tsx`
- Create: `site/components/MdxComponents.tsx`

- [ ] **Step 1: Create `site/components/Callout.tsx`**

```tsx
import { Info, AlertTriangle, AlertOctagon } from 'lucide-react'

interface CalloutProps {
  type: 'note' | 'warning' | 'danger'
  children: React.ReactNode
}

const variants = {
  note:    { border: 'border-blue-500',  bg: 'bg-blue-500/10',  Icon: Info,          text: 'text-blue-400' },
  warning: { border: 'border-amber-500', bg: 'bg-amber-500/10', Icon: AlertTriangle, text: 'text-amber-400' },
  danger:  { border: 'border-red-500',   bg: 'bg-red-500/10',   Icon: AlertOctagon,  text: 'text-red-400' },
}

export default function Callout({ type, children }: CalloutProps) {
  const { border, bg, Icon, text } = variants[type]
  return (
    <div className={`flex gap-3 rounded-r-lg border-l-4 ${border} ${bg} px-4 py-3 my-4`}>
      <Icon size={16} className={`${text} flex-shrink-0 mt-0.5`} />
      <div className="text-sm text-text-primary leading-relaxed">{children}</div>
    </div>
  )
}
```

- [ ] **Step 2: Create `site/components/MdxComponents.tsx`**

```tsx
import type { MDXComponents } from 'mdx/types'
import Callout from './Callout'

export const mdxComponents: MDXComponents = {
  // Callout shortcodes
  Note:    ({ children }: { children: React.ReactNode }) => <Callout type="note">{children}</Callout>,
  Warning: ({ children }: { children: React.ReactNode }) => <Callout type="warning">{children}</Callout>,
  Danger:  ({ children }: { children: React.ReactNode }) => <Callout type="danger">{children}</Callout>,

  // Block elements
  pre: ({ children, ...props }: React.HTMLProps<HTMLPreElement>) => (
    <pre
      className="overflow-x-auto rounded-lg border border-border bg-code-bg p-4 my-4 text-sm font-mono"
      {...props}
    >
      {children}
    </pre>
  ),
  blockquote: ({ children }: { children: React.ReactNode }) => (
    <blockquote className="border-l-4 border-accent pl-4 my-4 text-text-muted italic">
      {children}
    </blockquote>
  ),

  // Inline elements
  code: ({ children, ...props }: React.HTMLProps<HTMLElement>) => (
    <code
      className="font-mono text-sm bg-code-bg text-accent px-1.5 py-0.5 rounded"
      {...props}
    >
      {children}
    </code>
  ),
  a: ({ href, children }: React.HTMLProps<HTMLAnchorElement>) => (
    <a
      href={href}
      className="text-accent hover:text-accent-hover underline underline-offset-2 transition-colors"
    >
      {children}
    </a>
  ),

  // Headings
  h1: ({ children, id }: React.HTMLProps<HTMLHeadingElement>) => (
    <h1 id={id} className="text-3xl font-bold text-text-primary mt-8 mb-4 scroll-mt-20">{children}</h1>
  ),
  h2: ({ children, id }: React.HTMLProps<HTMLHeadingElement>) => (
    <h2 id={id} className="text-xl font-semibold text-text-primary mt-8 mb-3 border-b border-border pb-2 scroll-mt-20">{children}</h2>
  ),
  h3: ({ children, id }: React.HTMLProps<HTMLHeadingElement>) => (
    <h3 id={id} className="text-base font-semibold text-text-primary mt-6 mb-2 scroll-mt-20">{children}</h3>
  ),

  // Typography
  p:  ({ children }: { children: React.ReactNode }) => (
    <p className="text-text-primary leading-relaxed my-4">{children}</p>
  ),
  ul: ({ children }: { children: React.ReactNode }) => (
    <ul className="list-disc pl-6 my-4 space-y-1.5 text-text-primary">{children}</ul>
  ),
  ol: ({ children }: { children: React.ReactNode }) => (
    <ol className="list-decimal pl-6 my-4 space-y-1.5 text-text-primary">{children}</ol>
  ),
  li: ({ children }: { children: React.ReactNode }) => (
    <li className="leading-relaxed text-sm">{children}</li>
  ),

  // Tables
  table: ({ children }: { children: React.ReactNode }) => (
    <div className="overflow-x-auto my-6 rounded-lg border border-border">
      <table className="w-full text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }: { children: React.ReactNode }) => (
    <thead className="bg-surface border-b border-border">{children}</thead>
  ),
  th: ({ children }: { children: React.ReactNode }) => (
    <th className="px-4 py-2.5 text-left font-semibold text-text-muted">{children}</th>
  ),
  td: ({ children }: { children: React.ReactNode }) => (
    <td className="px-4 py-2.5 text-text-primary border-b border-border last-row:border-0">{children}</td>
  ),
  tr: ({ children }: { children: React.ReactNode }) => (
    <tr className="border-b border-border last:border-0 hover:bg-surface/50 transition-colors">{children}</tr>
  ),
}
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/components/Callout.tsx site/components/MdxComponents.tsx
git commit -m "feat(site): Callout and MdxComponents"
```

---

### Task 9: Sidebar + TOC components

**Files:**
- Create: `site/components/Sidebar.tsx`
- Create: `site/components/Toc.tsx`

- [ ] **Step 1: Create `site/components/Sidebar.tsx`**

```tsx
'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { NavSection } from '@/lib/nav'

interface SidebarProps {
  nav: NavSection[]
  basePath: '/docs' | '/api-reference'
}

export default function Sidebar({ nav, basePath }: SidebarProps) {
  const pathname = usePathname()

  return (
    <nav className="w-60 flex-shrink-0 hidden lg:block">
      {nav.map(section => (
        <div key={section.title} className="mb-8">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-text-muted mb-3 px-3">
            {section.title}
          </p>
          <ul className="space-y-0.5">
            {section.items.map(item => {
              const href = `${basePath}/${item.slug}`
              const active = pathname === href
              return (
                <li key={item.slug}>
                  <Link
                    href={href}
                    className={`block text-sm px-3 py-1.5 rounded-md transition-colors ${
                      active
                        ? 'bg-accent/10 text-accent font-medium'
                        : 'text-text-muted hover:text-text-primary hover:bg-surface'
                    }`}
                  >
                    {item.title}
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </nav>
  )
}
```

- [ ] **Step 2: Create `site/components/Toc.tsx`**

```tsx
'use client'
import { useEffect, useState } from 'react'
import type { Heading } from '@/lib/mdx'

export default function Toc({ headings }: { headings: Heading[] }) {
  const [active, setActive] = useState('')

  useEffect(() => {
    if (headings.length === 0) return

    const observer = new IntersectionObserver(
      entries => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActive(entry.target.id)
            break
          }
        }
      },
      { rootMargin: '-80px 0px -60% 0px' }
    )

    headings.forEach(h => {
      const el = document.getElementById(h.id)
      if (el) observer.observe(el)
    })

    return () => observer.disconnect()
  }, [headings])

  if (headings.length === 0) return null

  return (
    <aside className="w-52 flex-shrink-0 hidden xl:block">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-text-muted mb-3">
        On this page
      </p>
      <ul className="space-y-1">
        {headings.map(h => (
          <li key={h.id} style={{ paddingLeft: `${(h.level - 1) * 12}px` }}>
            <a
              href={`#${h.id}`}
              className={`block text-xs py-0.5 transition-colors hover:text-text-primary ${
                active === h.id ? 'text-accent font-medium' : 'text-text-muted'
              }`}
            >
              {h.text}
            </a>
          </li>
        ))}
      </ul>
    </aside>
  )
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/components/Sidebar.tsx site/components/Toc.tsx
git commit -m "feat(site): Sidebar and Toc components"
```

---

### Task 10: Docs layout + dynamic route

**Files:**
- Create: `site/app/docs/layout.tsx`
- Create: `site/app/docs/[[...slug]]/page.tsx`

- [ ] **Step 1: Create `site/app/docs/layout.tsx`**

```tsx
import { docsNav } from '@/lib/nav'
import Sidebar from '@/components/Sidebar'

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-7xl px-6 py-12">
      <div className="flex gap-12">
        <Sidebar nav={docsNav} basePath="/docs" />
        <div className="flex-1 min-w-0 flex gap-12">
          {children}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `site/app/docs/[[...slug]]/page.tsx`**

```tsx
import { notFound, redirect } from 'next/navigation'
import { compileMDX } from 'next-mdx-remote/rsc'
import { getAllSlugs, getDocMeta } from '@/lib/mdx'
import { mdxComponents } from '@/components/MdxComponents'
import Toc from '@/components/Toc'
import type { Metadata } from 'next'

interface Props {
  params: { slug?: string[] }
}

export async function generateStaticParams() {
  const slugs = getAllSlugs('docs')
  return [{ slug: undefined }, ...slugs.map(s => ({ slug: s }))]
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const slug = params.slug ?? ['introduction']
  const meta = getDocMeta('docs', slug)
  if (!meta) return {}
  return {
    title: meta.frontmatter.title,
    description: meta.frontmatter.description,
  }
}

export default async function DocsPage({ params }: Props) {
  if (!params.slug) redirect('/docs/introduction')

  const meta = getDocMeta('docs', params.slug)
  if (!meta) notFound()

  const { content } = await compileMDX({
    source: meta.rawContent,
    components: mdxComponents,
  })

  return (
    <>
      <article className="flex-1 min-w-0 max-w-3xl">
        <h1 className="text-3xl font-bold text-text-primary mb-2">{meta.frontmatter.title}</h1>
        {meta.frontmatter.description && (
          <p className="text-text-muted mb-8 text-lg leading-relaxed">{meta.frontmatter.description}</p>
        )}
        <div>{content}</div>
      </article>
      <Toc headings={meta.headings} />
    </>
  )
}
```

- [ ] **Step 3: Create a minimal fixture to verify build**

Create `site/content/docs/introduction.mdx`:
```mdx
---
title: Introduction
description: What Claudhaus is and why you'd want to run it.
---

Claudhaus is a self-hosted personal AI agent built on the Claude Agent SDK.
```

- [ ] **Step 4: Build and verify**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm run build 2>&1 | tail -10
```

Expected: `Export successful`. Pages like `out/docs/introduction.html` exist.

- [ ] **Step 5: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/app/docs/ site/content/docs/introduction.mdx
git commit -m "feat(site): docs layout, dynamic route, introduction fixture"
```

---

### Task 11: API reference layout + dynamic route

**Files:**
- Create: `site/app/api-reference/layout.tsx`
- Create: `site/app/api-reference/[[...slug]]/page.tsx`

- [ ] **Step 1: Create `site/app/api-reference/layout.tsx`**

```tsx
import { apiNav } from '@/lib/nav'
import Sidebar from '@/components/Sidebar'

export default function ApiReferenceLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-7xl px-6 py-12">
      <div className="flex gap-12">
        <Sidebar nav={apiNav} basePath="/api-reference" />
        <div className="flex-1 min-w-0 flex gap-12">
          {children}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create `site/app/api-reference/[[...slug]]/page.tsx`**

```tsx
import { notFound, redirect } from 'next/navigation'
import { compileMDX } from 'next-mdx-remote/rsc'
import { getAllSlugs, getDocMeta } from '@/lib/mdx'
import { mdxComponents } from '@/components/MdxComponents'
import Toc from '@/components/Toc'
import type { Metadata } from 'next'

interface Props {
  params: { slug?: string[] }
}

export async function generateStaticParams() {
  const slugs = getAllSlugs('api')
  return [{ slug: undefined }, ...slugs.map(s => ({ slug: s }))]
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const slug = params.slug ?? ['overview']
  const meta = getDocMeta('api', slug)
  if (!meta) return {}
  return {
    title: meta.frontmatter.title,
    description: meta.frontmatter.description,
  }
}

export default async function ApiReferencePage({ params }: Props) {
  if (!params.slug) redirect('/api-reference/overview')

  const meta = getDocMeta('api', params.slug)
  if (!meta) notFound()

  const { content } = await compileMDX({
    source: meta.rawContent,
    components: mdxComponents,
  })

  return (
    <>
      <article className="flex-1 min-w-0 max-w-3xl">
        <h1 className="text-3xl font-bold text-text-primary mb-2">{meta.frontmatter.title}</h1>
        {meta.frontmatter.description && (
          <p className="text-text-muted mb-8 text-lg leading-relaxed">{meta.frontmatter.description}</p>
        )}
        <div>{content}</div>
      </article>
      <Toc headings={meta.headings} />
    </>
  )
}
```

- [ ] **Step 3: Create a minimal fixture**

Create `site/content/api/overview.mdx`:
```mdx
---
title: API Reference Overview
description: Tools and commands available in Claudhaus.
---

Claudhaus exposes two categories of tools: built-in filesystem tools and agent SDK tools.
```

- [ ] **Step 4: Build and verify**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm run build 2>&1 | tail -5
```

Expected: `Export successful`.

- [ ] **Step 5: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/app/api-reference/ site/content/api/overview.mdx
git commit -m "feat(site): API reference layout and dynamic route"
```

---

### Task 12: Pagefind search

**Files:**
- Create: `site/components/Search.tsx`
- Modify: `site/components/Nav.tsx`

- [ ] **Step 1: Create `site/components/Search.tsx`**

```tsx
'use client'
import { useEffect, useState, useCallback, useRef } from 'react'
import { Search as SearchIcon } from 'lucide-react'

interface SearchResult {
  url: string
  title: string
  excerpt: string
}

declare global {
  interface Window {
    pagefind?: {
      search: (q: string) => Promise<{
        results: Array<{ data: () => Promise<{ url: string; excerpt: string; meta: { title: string } }> }>
      }>
    }
  }
}

export default function Search() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  // Keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setOpen(o => !o)
      }
      if (e.key === 'Escape') setOpen(false)
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // Focus input on open
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50)
    else { setQuery(''); setResults([]) }
  }, [open])

  // Lazy-load Pagefind script
  useEffect(() => {
    if (open && !window.pagefind) {
      const script = document.createElement('script')
      script.src = '/pagefind/pagefind.js'
      script.type = 'module'
      document.head.appendChild(script)
    }
  }, [open])

  const runSearch = useCallback(async (q: string) => {
    if (!q.trim() || !window.pagefind) { setResults([]); return }
    try {
      const res = await window.pagefind.search(q)
      const data = await Promise.all(res.results.slice(0, 8).map(r => r.data()))
      setResults(data.map(d => ({ url: d.url, title: d.meta.title, excerpt: d.excerpt })))
    } catch {
      setResults([])
    }
  }, [])

  useEffect(() => { runSearch(query) }, [query, runSearch])

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border text-text-muted text-sm hover:border-accent transition-colors"
      >
        <SearchIcon size={13} />
        <span>Search</span>
        <kbd className="ml-1 text-xs bg-surface px-1.5 py-0.5 rounded border border-border">⌘K</kbd>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-background/80 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-xl bg-surface border border-border rounded-xl shadow-2xl overflow-hidden mx-4"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 px-4 py-3 border-b border-border">
              <SearchIcon size={16} className="text-text-muted flex-shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search documentation..."
                className="flex-1 bg-transparent text-text-primary placeholder-text-muted outline-none text-sm"
              />
              <kbd className="text-xs text-text-muted bg-background px-1.5 py-0.5 rounded border border-border">
                Esc
              </kbd>
            </div>

            {results.length > 0 && (
              <ul className="divide-y divide-border max-h-80 overflow-y-auto">
                {results.map(r => (
                  <li key={r.url}>
                    <a
                      href={r.url}
                      className="block px-4 py-3 hover:bg-background transition-colors"
                      onClick={() => setOpen(false)}
                    >
                      <p className="text-sm font-medium text-text-primary">{r.title}</p>
                      <p
                        className="text-xs text-text-muted mt-0.5 line-clamp-2"
                        dangerouslySetInnerHTML={{ __html: r.excerpt }}
                      />
                    </a>
                  </li>
                ))}
              </ul>
            )}

            {query && results.length === 0 && (
              <p className="px-4 py-6 text-sm text-text-muted text-center">
                No results for &quot;{query}&quot;
              </p>
            )}
          </div>
        </div>
      )}
    </>
  )
}
```

- [ ] **Step 2: Add Search to `site/components/Nav.tsx`**

Add `import Search from './Search'` and insert `<Search />` between the center nav links and the right-side buttons group:

```tsx
import Link from 'next/link'
import { Github } from 'lucide-react'
import ThemeToggle from './ThemeToggle'
import Search from './Search'

export default function Nav() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="mx-auto max-w-7xl flex items-center justify-between h-14 px-6">
        <Link href="/" className="font-semibold text-text-primary tracking-tight text-sm">
          claudhaus
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm text-text-muted">
          <Link href="/docs" className="hover:text-text-primary transition-colors">Docs</Link>
          <Link href="/api-reference" className="hover:text-text-primary transition-colors">API Reference</Link>
          <a
            href="https://github.com/JjayFabor/claudhaus"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-text-primary transition-colors flex items-center gap-1.5"
          >
            <Github size={14} />
            GitHub
          </a>
        </nav>

        <div className="flex items-center gap-2">
          <Search />
          <ThemeToggle />
          <Link
            href="/docs/introduction"
            className="px-4 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors"
          >
            Get Started
          </Link>
        </div>
      </div>
    </header>
  )
}
```

- [ ] **Step 3: Build and verify**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm run build 2>&1 | tail -5
```

Expected: `Export successful`.

- [ ] **Step 4: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/components/Search.tsx site/components/Nav.tsx
git commit -m "feat(site): Pagefind search modal (Cmd+K)"
```

---

### Task 13: Docs MDX content — Getting Started + Core Concepts

**Files:**
- Create: `site/content/docs/introduction.mdx` (overwrite fixture)
- Create: `site/content/docs/prerequisites.mdx`
- Create: `site/content/docs/quick-start.mdx`
- Create: `site/content/docs/configuration.mdx`
- Create: `site/content/docs/memory.mdx`
- Create: `site/content/docs/skills.mdx`
- Create: `site/content/docs/connectors.mdx`
- Create: `site/content/docs/sub-agents.mdx`
- Create: `site/content/docs/scheduler.mdx`

- [ ] **Step 1: Write `site/content/docs/introduction.mdx`**

```mdx
---
title: Introduction
description: What Claudhaus is and why you'd want to run it.
---

Claudhaus is a self-hosted personal AI agent built on the Claude Agent SDK. You connect it to Telegram, define its role, and it gets smarter every time you chat with it.

It is **not** a chatbot. It is an agent — it can run shell commands, read and write files, call external APIs, schedule recurring tasks, and improve its own source code. You control what it can do and who can talk to it.

## Why self-host?

A Claude Code subscription covers Claudhaus's usage at no extra cost. Everything runs on your own machine. Your conversations, memory, and data never leave your infrastructure.

## What it is not

- **Not a team tool.** Claudhaus is designed for one person or a household. There is no user management, no roles, no permissions system.
- **Not a SaaS product.** There is no subscription, no dashboard login. You run the code.
- **Not affiliated with Anthropic.** Claudhaus is an independent open-source project.

## Next steps

<Note>Start with Prerequisites to confirm your environment is ready before running setup.</Note>

- [Prerequisites](/docs/prerequisites) — what you need installed
- [Quick Start](/docs/quick-start) — get running in under 5 minutes
- [Configuration](/docs/configuration) — environment variables reference
```

- [ ] **Step 2: Write `site/content/docs/prerequisites.mdx`**

```mdx
---
title: Prerequisites
description: What you need installed before running Claudhaus.
---

## Required

| Requirement | Version | Notes |
|---|---|---|
| Claude Code subscription | Active | Must be logged in via the `claude` CLI |
| Python | 3.10+ | Run `python3 --version` to check |
| Node.js | 18+ | Required by the Claude CLI and MCP servers |
| git | Any | For cloning the repo |
| Telegram account | — | To create a bot via BotFather |

<Warning>Do not set `ANTHROPIC_API_KEY`. Claudhaus authenticates via your Claude Code subscription (`~/.claude/.credentials.json`). Setting that env var switches billing from your subscription to metered API calls.</Warning>

## Verify your environment

Run all four commands — all should succeed before proceeding:

```bash
claude --version    # e.g. 1.2.3
python3 --version   # Python 3.10.x or higher
node --version      # v18.x or higher
git --version       # git version 2.x
```

## Optional

| Optional | When needed |
|---|---|
| OpenAI API key | Only if `WHISPER_PROVIDER=openai` for voice transcription |
| Discord bot token | Only if you want a Discord interface alongside Telegram |
```

- [ ] **Step 3: Write `site/content/docs/quick-start.mdx`**

```mdx
---
title: Quick Start
description: Get Claudhaus running in under 5 minutes.
---

## 1. Clone the repo

```bash
git clone https://github.com/JjayFabor/claudhaus.git
cd claudhaus
```

## 2. Run the setup wizard

```bash
python3 scripts/setup.py
```

The wizard will:

1. Check your prerequisites (`claude`, `python3`, `node`, `git`)
2. Create `.env` from `.env.example`
3. Prompt for your Telegram bot token (get one from [@BotFather](https://t.me/BotFather) — send `/newbot`)
4. Create runtime directories (`data/`, `logs/`, `workspaces/`)
5. Install Python dependencies into `.venv`
6. Initialize the SQLite database
7. Optionally install systemd user units on Linux/WSL2

## 3. Find your Telegram user ID

Start the bot and send it `/whoami`:

```bash
source .venv/bin/activate
python agents/main/agent.py
```

The bot replies with your numeric user ID. Add it to `.env`:

```bash
TELEGRAM_ALLOWED_USER_IDS=123456789
```

Then restart the bot.

## 4. Customize your agent

Edit `agents/shared/USER_PROFILE.md` with your name, role, timezone, and any context that helps the agent understand you. This is what makes it feel like yours.

## 5. Start chatting

```bash
source .venv/bin/activate
python agents/main/agent.py
```

Or with systemd: `systemctl --user start claude-main.service`

<Note>The first message in a new session takes a few seconds while the Claude CLI initializes. Subsequent messages are much faster.</Note>

## What to do next

- Say "what can you do?" to explore capabilities
- Say "remember that I prefer concise replies" to teach a preference
- Say "add the GitHub connector" to connect your first integration
```

- [ ] **Step 4: Write `site/content/docs/configuration.mdx`**

```mdx
---
title: Configuration
description: Environment variables reference for Claudhaus.
---

All configuration lives in `.env` in the project root. Copy `.env.example` to get started — the setup wizard does this automatically.

## Telegram

| Variable | Default | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | Your bot token from [@BotFather](https://t.me/BotFather) |
| `TELEGRAM_ALLOWED_USER_IDS` | — | Comma-separated Telegram user IDs who can use the bot |
| `TELEGRAM_ALLOWED_CHAT_IDS` | — | Group/channel IDs (if empty, DMs only) |

## Agent behavior

| Variable | Default | Description |
|---|---|---|
| `MAIN_EXTRA_TOOLS` | `*` | `*` = all tools; comma-list to restrict (e.g. `Bash,Read,Write`) |

## Voice transcription

| Variable | Default | Description |
|---|---|---|
| `WHISPER_PROVIDER` | `none` | `none`, `openai`, or `local` |
| `OPENAI_API_KEY` | — | Required when `WHISPER_PROVIDER=openai` |

## Discord

| Variable | Default | Description |
|---|---|---|
| `DISCORD_BOT_TOKEN` | — | Discord bot token (leave blank to disable Discord) |
| `DISCORD_ALLOWED_USER_IDS` | — | Comma-separated Discord user IDs (empty = allow all) |
| `DISCORD_ALLOWED_GUILD_IDS` | — | Comma-separated server IDs (empty = allow all) |

## Dreaming (nightly memory consolidation)

| Variable | Default | Description |
|---|---|---|
| `DREAMING_ENABLED` | `false` | Enable nightly memory sweep |
| `DREAMING_LOOKBACK_DAYS` | `30` | Days of daily notes to sweep |
| `DREAMING_PROMOTION_THRESHOLD` | `0.6` | Score threshold to promote a memory to `DREAMS.md` |

## Dashboard

| Variable | Default | Description |
|---|---|---|
| `DASHBOARD_PORT` | `8000` | Port for the internal dashboard |

<Warning>Never commit `.env` to git. It is gitignored by default. Keep your bot token and API keys private.</Warning>
```

- [ ] **Step 5: Write `site/content/docs/memory.mdx`**

```mdx
---
title: Memory
description: How Claudhaus remembers facts, preferences, and context across sessions.
---

Memory in Claudhaus is plain Markdown — readable and editable directly. There are three layers:

## MEMORY.md

Durable facts and preferences that apply to every session. The agent reads this at the start of conversations that reference past context and appends to it via the `learn` tool.

Examples of what lives here:
- Your name and role
- Preferred reply style ("always concise unless asked for detail")
- Business context ("we use NZD for all amounts")
- Technical stack ("the API is Python + FastAPI, deployed on Render")

## Daily notes

Located at `~/memory/YYYY-MM-DD.md`. Each day's session context is appended here — what you worked on, decisions made, tasks completed. The agent creates the file if it doesn't exist.

## DREAMS.md

Insights promoted from daily notes during the nightly dreaming sweep. When `DREAMING_ENABLED=true`, the agent reviews recent daily notes, scores recurring patterns, and promotes high-scoring insights to `DREAMS.md`. These become part of the long-term memory layer.

## How retrieval works

Claudhaus uses BM25 full-text search over all memory files. When a message seems to reference past context, the agent searches and injects relevant excerpts into the session. You don't need to ask it to remember — it does this automatically.

## Teaching the agent

```
"Remember that I prefer bullet points over prose"
"Always use metric units in your answers"
"We use GitHub for all code, not GitLab"
```

These phrases trigger the `learn` tool, which writes the fact to the appropriate memory file.
```

- [ ] **Step 6: Write `site/content/docs/skills.mdx`**

```mdx
---
title: Skills
description: Reusable workflows injected into the agent's system prompt.
---

Skills are Markdown files stored in `agents/main/skills/`. On each turn, the agent injects relevant skills into its system prompt — giving it domain knowledge, formatting rules, or step-by-step workflows without needing a restart.

## Two loading modes

**Always-inject** (default): skills without frontmatter are included on every turn.

**Trigger-based**: skills with frontmatter are only injected when a trigger word appears in the message.

```markdown
---
always: false
triggers: [backlog, report, schedule]
description: Daily backlog report formatting
---

# Morning Backlog Report

When the user asks for a backlog report, format it as...
```

## Managing skills via chat

```
"create a skill called morning-report that formats daily standup notes"
"list all skills"
"read the morning-report skill"
"delete the morning-report skill"
```

Or use the tools directly: `skill_list`, `skill_read`, `skill_write`, `skill_delete`.

## Hot-loaded

Skills take effect immediately — no restart needed. The agent reads the file on the next turn.

## When to use a skill

- You've explained the same workflow to the agent more than once
- You want consistent formatting for a specific type of output
- You have domain knowledge the agent should always have available
```

- [ ] **Step 7: Write `site/content/docs/connectors.mdx`**

```mdx
---
title: Connectors
description: Self-installing MCP integrations for external services.
---

Connectors are MCP (Model Context Protocol) servers that give the agent access to external services — GitHub, HubSpot, Slack, Notion, and more.

## Adding a connector

Just ask the agent:

```
"add the GitHub connector"
"connect to HubSpot"
"I want to use Slack"
```

The agent:
1. Calls `connector_info` to find out what credentials are required
2. Tells you exactly what to provide and where to get it
3. Calls `connector_add` with your credentials
4. Restarts automatically

<Warning>The bot goes offline briefly during the restart after adding a connector. This is expected — it takes a few seconds.</Warning>

## Available connectors

Claudhaus supports any MCP server. Common ones include GitHub, HubSpot, Slack, Notion, Google Drive, and custom servers you build yourself.

## After connecting

The connector's tools become available immediately in the next session. The agent knows what tools each connector provides and uses them naturally in conversation.

## Removing a connector

```
"remove the GitHub connector"
```

The bot restarts again after removal.
```

- [ ] **Step 8: Write `site/content/docs/sub-agents.mdx`**

```mdx
---
title: Sub-agents
description: Spawn focused AI specialists with their own workspaces and tool sets.
---

Sub-agents are separate Claude sessions with their own system prompt, tool set, and workspace. The main agent spawns them for focused work — research, code review, data processing — and gets the result back.

## Creating a sub-agent

```
"create a sub-agent called researcher that searches the web and summarizes findings"
```

Or directly:

```
subagent_create(
  name="researcher",
  description="Searches and summarizes web content",
  system_prompt="You are a research specialist...",
  tools=["WebSearch", "WebFetch", "Read"]
)
```

## Running a sub-agent

```
"ask the researcher to find everything published about Claude Agent SDK in the last 30 days"
```

Or:

```
subagent_run(name="researcher", task="Find recent publications about Claude Agent SDK")
```

The main agent waits for the result and incorporates it into its response.

## Design principles

- **Minimal tools** — give sub-agents only what they need, not `*`
- **Focused system prompt** — narrow scope produces better results
- **Clear task descriptions** — the sub-agent starts with no context except its system prompt and the task

## Listing sub-agents

```
subagent_list()
```

Returns all defined sub-agents with their name and description.
```

- [ ] **Step 9: Write `site/content/docs/scheduler.mdx`**

```mdx
---
title: Scheduler
description: Schedule recurring and one-shot tasks that run automatically.
---

The scheduler lets you set up tasks that run on a timer — daily reports, periodic checks, reminders — without you having to trigger them manually.

## Recurring tasks

```
"check GitHub for open PRs every morning at 9am and send me a summary"
"run a memory consolidation sweep every Sunday at midnight"
```

Or:

```
scheduler_add(
  task="Summarize open GitHub PRs and send_message the results",
  schedule_str="every day at 9am"
)
```

`schedule_str` accepts natural language: `"every 30 minutes"`, `"every 2 hours"`, `"every day at 9am"`, `"every Monday at 8am"`.

## One-shot tasks

```
"remind me to review the PR in 2 hours"
"at 3pm, check if the staging deploy finished"
```

Or:

```
schedule_once(
  task="send_message('Time to review the PR')",
  when_str="in 2 hours"
)
```

`when_str` accepts: `"in 30 minutes"`, `"in 2 hours"`, `"at 3pm"`, `"tomorrow at 9am"`.

## Managing scheduled tasks

```
scheduler_list()      # see all tasks with their IDs and schedules
scheduler_remove(id)  # remove a recurring task by ID
```

## Persistence

Scheduled tasks survive restarts. They are stored in the SQLite database and reloaded when the agent starts.
```

- [ ] **Step 10: Verify build with all new files**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm run build 2>&1 | tail -5
```

Expected: `Export successful`.

- [ ] **Step 11: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/content/docs/
git commit -m "feat(site): docs content — Getting Started and Core Concepts"
```

---

### Task 14: Docs MDX content — Guides

**Files:**
- Create: `site/content/docs/guides/connecting-telegram.mdx`
- Create: `site/content/docs/guides/adding-a-connector.mdx`
- Create: `site/content/docs/guides/writing-a-skill.mdx`
- Create: `site/content/docs/guides/wsl2-setup.mdx`
- Create: `site/content/docs/guides/linux-setup.mdx`
- Create: `site/content/docs/guides/macos-setup.mdx`
- Create: `site/content/docs/guides/docker-setup.mdx`

- [ ] **Step 1: Write `site/content/docs/guides/connecting-telegram.mdx`**

```mdx
---
title: Connecting Telegram
description: Create a Telegram bot and connect it to Claudhaus.
---

## 1. Create a bot via BotFather

Open Telegram and search for [@BotFather](https://t.me/BotFather). Send:

```
/newbot
```

Follow the prompts — choose a name and a username (must end in `bot`). BotFather replies with your bot token:

```
Use this token to access the HTTP API:
7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 2. Add the token to `.env`

```bash
TELEGRAM_BOT_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 3. Start the bot

```bash
source .venv/bin/activate
python agents/main/agent.py
```

## 4. Find your user ID

Open Telegram and send your bot `/whoami`. It replies:

```
Your chat ID: 123456789
Your user ID: 123456789
Username: @yourhandle
```

## 5. Allow yourself access

Add your user ID to `.env`:

```bash
TELEGRAM_ALLOWED_USER_IDS=123456789
```

Restart the bot. You can now send it messages and it will respond.

## 6. Test it

Send `/start` — the bot should greet you. Send "what can you do?" to explore its capabilities.

<Note>Only user IDs in `TELEGRAM_ALLOWED_USER_IDS` can interact with the bot. Anyone else gets no response.</Note>
```

- [ ] **Step 2: Write `site/content/docs/guides/adding-a-connector.mdx`**

```mdx
---
title: Adding a Connector
description: How to connect Claudhaus to external services via MCP.
---

Connectors give the agent access to external services. The entire setup happens via chat — no config files.

## The flow

**1. Ask the agent to add the connector:**

```
"add the GitHub connector"
```

**2. The agent calls `connector_info` and tells you what credentials are needed:**

```
To connect GitHub I need:
- GITHUB_TOKEN: a Personal Access Token with repo scope
  Get one at: https://github.com/settings/tokens
```

**3. Provide the credentials:**

```
"here's my GitHub token: ghp_xxxxxxxxxxxx"
```

**4. The agent calls `connector_add` and restarts.**

<Warning>The bot goes offline for a few seconds during the restart. This is normal.</Warning>

**5. After restart, the connector is live.**

The agent now has access to GitHub tools — creating PRs, reading issues, searching code, etc.

## Common connectors

| Service | What you need |
|---|---|
| GitHub | Personal Access Token (repo scope) |
| HubSpot | Private App token |
| Slack | Bot token + App token |
| Notion | Integration token |
| Google Drive | OAuth credentials |

## Removing a connector

```
"remove the GitHub connector"
```

The bot restarts again after removal.
```

- [ ] **Step 3: Write `site/content/docs/guides/writing-a-skill.mdx`**

```mdx
---
title: Writing a Skill
description: How to create reusable workflows for your agent.
---

A skill is a Markdown file that gets injected into the agent's system prompt. Write one when you've explained the same workflow more than once, or when you want consistent formatting for a specific type of output.

## Creating via chat

The easiest way:

```
"create a skill called morning-report: when I ask for a morning report,
 pull open GitHub PRs, format them as a numbered list with assignee and
 age in days, then summarize blockers"
```

The agent writes the skill file and confirms. It takes effect immediately.

## Skill file format

Skills live in `agents/main/skills/`. Each is a Markdown file:

```markdown
# Morning Report

When the user asks for a morning report:
1. Call subagent_run(name="github-reader", task="list open PRs with assignee and age")
2. Format the results as a numbered list
3. Identify any PRs older than 3 days as blockers
4. End with a one-line summary
```

## Trigger-based skills (load on demand)

Add frontmatter to only inject the skill when a trigger word appears:

```markdown
---
always: false
triggers: [morning report, standup, daily summary]
description: Morning standup report formatting
---

# Morning Report
...
```

This keeps the system prompt lean — the skill is only loaded when relevant.

## Managing skills

```
skill_list()                    # see all skills
skill_read(name="morning-report")  # read a skill
skill_write(name="morning-report", content="...")  # create or update
skill_delete(name="morning-report")  # remove
```

Or just ask the agent in plain language.
```

- [ ] **Step 4: Write `site/content/docs/guides/wsl2-setup.mdx`**

```mdx
---
title: WSL2 Setup
description: Running Claudhaus persistently on WSL2.
---

WSL2 can shut down idle instances, which kills your bot. Two settings prevent this.

## 1. Enable systemd

Edit `/etc/wsl.conf` (create it if it doesn't exist):

```ini
[boot]
systemd=true
```

Restart WSL: in PowerShell, run `wsl --shutdown` then reopen your WSL terminal.

## 2. Disable idle timeout

Create or edit `~/.wslconfig` (in your Windows home directory, e.g. `C:\Users\you\.wslconfig`):

```ini
[wsl2]
vmIdleTimeout=-1
```

Restart WSL again.

## 3. Install systemd units

```bash
bash scripts/install-systemd.sh
```

This copies all unit files, enables linger (so units survive logout), starts `claude-main.service`, and enables the nightly backup and dreaming timers.

## 4. Verify

```bash
systemctl --user status claude-main.service
```

Expected: `active (running)`.

## 5. View logs

```bash
journalctl --user -u claude-main.service -f
```
```

- [ ] **Step 5: Write `site/content/docs/guides/linux-setup.mdx`**

```mdx
---
title: Linux Setup
description: Running Claudhaus as a systemd user service on Linux.
---

## Install systemd units

```bash
bash scripts/install-systemd.sh
```

This script:
1. Copies unit files to `~/.config/systemd/user/`
2. Runs `loginctl enable-linger` so units survive logout
3. Starts `claude-main.service`
4. Enables nightly backup (`claude-backup.timer`) and dreaming (`claude-dreaming.timer`) timers

## Verify the service is running

```bash
systemctl --user status claude-main.service
```

Expected: `active (running)`.

## View logs

```bash
journalctl --user -u claude-main.service -f
```

## Restart after config changes

```bash
systemctl --user restart claude-main.service
```

## Enable on boot (if not done by the install script)

```bash
loginctl enable-linger $USER
systemctl --user enable claude-main.service
```
```

- [ ] **Step 6: Write `site/content/docs/guides/macos-setup.mdx`**

```mdx
---
title: macOS Setup
description: Running Claudhaus as a launchd agent on macOS.
---

## Copy the plist

```bash
cp systemd/com.claudecommandcenter.main.plist ~/Library/LaunchAgents/
```

## Load the agent

```bash
launchctl load ~/Library/LaunchAgents/com.claudecommandcenter.main.plist
```

## Verify it's running

```bash
launchctl list | grep claudecommandcenter
```

Expected: a line with `com.claudecommandcenter.main` and a PID (not `-`).

## View logs

Logs are written to `logs/main.log` in the project directory.

## Unload (stop)

```bash
launchctl unload ~/Library/LaunchAgents/com.claudecommandcenter.main.plist
```

## Reload after config changes

```bash
launchctl unload ~/Library/LaunchAgents/com.claudecommandcenter.main.plist
launchctl load   ~/Library/LaunchAgents/com.claudecommandcenter.main.plist
```

<Note>The plist uses your local Python path. If you installed Python with Homebrew or pyenv, verify the path in the plist matches `which python3`.</Note>
```

- [ ] **Step 7: Write `site/content/docs/guides/docker-setup.mdx`**

```mdx
---
title: Docker Setup
description: Running Claudhaus in a Docker container.
---

## Start the container

```bash
docker compose up -d
```

## Critical: the `~/.claude` volume mount

Claudhaus authenticates via the Claude CLI (`~/.claude/.credentials.json`). The `docker-compose.yml` mounts your local `~/.claude` directory into the container. Without this mount, the CLI cannot authenticate and the bot will not start.

<Danger>Do not remove the `~/.claude` volume mount from `docker-compose.yml`. The bot will fail to start without Claude CLI credentials.</Danger>

## View logs

```bash
docker compose logs -f main
```

## Stop

```bash
docker compose down
```

## Rebuild after code changes

```bash
docker compose up -d --build
```

## Environment variables

All `.env` variables work the same in Docker. The `docker-compose.yml` loads `.env` automatically via `env_file: .env`.

## Volumes

The compose file creates two volumes:

| Mount | Purpose |
|---|---|
| `~/.claude:/root/.claude` | Claude CLI credentials (required) |
| `./data:/app/data` | SQLite database persistence |
| `./logs:/app/logs` | Log file persistence |
| `./agents:/app/agents` | Skills, memory, config |
```

- [ ] **Step 8: Build and verify**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm run build 2>&1 | tail -5
```

Expected: `Export successful`.

- [ ] **Step 9: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/content/docs/guides/
git commit -m "feat(site): docs guides — Telegram, connectors, skills, platform setup"
```

---

### Task 15: API reference MDX content

**Files:** All files in `site/content/api/`

- [ ] **Step 1: Write `site/content/api/overview.mdx`** (overwrite fixture)

```mdx
---
title: API Reference Overview
description: Tools and commands available in Claudhaus.
---

Claudhaus exposes two categories of tools to the Claude agent:

## Built-in filesystem tools

These are standard Claude Code tools available in every session:

| Tool | Purpose |
|---|---|
| [Bash](/api-reference/bash) | Run shell commands |
| [Read / Write / Edit](/api-reference/read-write-edit) | Read and modify files |
| [Glob / Grep](/api-reference/glob-grep) | Find files and search content |

## Agent SDK tools

These tools are added by Claudhaus and control the agent's extended capabilities:

| Category | Tools |
|---|---|
| Scheduling | `scheduler_add`, `scheduler_list`, `scheduler_remove`, `schedule_once` |
| Sub-agents | `subagent_list`, `subagent_create`, `subagent_run` |
| Connectors | `connector_info`, `connector_add` |
| Shared context | `share`, `revoke`, `shared` |
| Learning | `learn`, `skill_list`, `skill_read`, `skill_write`, `skill_delete` |

<Note>These are tools used by the agent internally, not an HTTP API. You interact with them via natural language in Telegram — the agent calls them on your behalf.</Note>
```

- [ ] **Step 2: Write `site/content/api/bash.mdx`**

```mdx
---
title: Bash
description: Run shell commands in the agent's environment.
---

Runs a shell command and returns stdout, stderr, and exit code.

## Parameters

| Name | Type | Required | Description |
|---|---|---|---|
| `command` | string | ✓ | The shell command to run |
| `timeout` | number | — | Timeout in milliseconds (default: 120000) |
| `description` | string | — | Human-readable label shown in the UI |

## Example

```json
{
  "command": "git status",
  "timeout": 10000
}
```

## Notes

- Claudhaus runs with `bypassPermissions` mode — the agent can execute commands without per-action prompts. Only run Claudhaus on machines you control.
- Long-running commands (builds, tests) should set an appropriate `timeout`.
- The agent confirms before destructive operations by default (configured in CLAUDE.md).
```

- [ ] **Step 3: Write `site/content/api/read-write-edit.mdx`**

```mdx
---
title: Read / Write / Edit
description: Read and modify files in the agent's workspace.
---

## Read

Reads a file and returns its contents.

| Name | Type | Required | Description |
|---|---|---|---|
| `file_path` | string | ✓ | Absolute path to the file |
| `limit` | number | — | Number of lines to read |
| `offset` | number | — | Line number to start from |

```json
{ "file_path": "/home/user/project/README.md", "limit": 50 }
```

## Write

Creates or overwrites a file with new content.

| Name | Type | Required | Description |
|---|---|---|---|
| `file_path` | string | ✓ | Absolute path to write |
| `content` | string | ✓ | Full file content |

```json
{ "file_path": "/home/user/project/notes.md", "content": "# Notes\n\nMeeting at 3pm." }
```

## Edit

Replaces a specific string within an existing file.

| Name | Type | Required | Description |
|---|---|---|---|
| `file_path` | string | ✓ | Absolute path to the file |
| `old_string` | string | ✓ | Exact text to find and replace |
| `new_string` | string | ✓ | Replacement text |
| `replace_all` | boolean | — | Replace all occurrences (default: false) |

```json
{
  "file_path": "/home/user/project/config.py",
  "old_string": "DEBUG = False",
  "new_string": "DEBUG = True"
}
```

<Note>Edit fails if `old_string` is not found in the file. Read the file first to confirm the exact text.</Note>
```

- [ ] **Step 4: Write `site/content/api/glob-grep.mdx`**

```mdx
---
title: Glob / Grep
description: Find files by pattern and search content.
---

## Glob

Finds files matching a glob pattern, sorted by modification time.

| Name | Type | Required | Description |
|---|---|---|---|
| `pattern` | string | ✓ | Glob pattern (e.g. `**/*.py`, `src/**/*.ts`) |
| `path` | string | — | Directory to search in (default: current working directory) |

```json
{ "pattern": "**/*.mdx", "path": "/home/user/site/content" }
```

## Grep

Searches file contents using ripgrep regex.

| Name | Type | Required | Description |
|---|---|---|---|
| `pattern` | string | ✓ | Regex pattern to search for |
| `path` | string | — | File or directory to search |
| `glob` | string | — | Glob filter (e.g. `*.py`) |
| `type` | string | — | File type (e.g. `py`, `ts`, `go`) |
| `output_mode` | string | — | `files_with_matches` (default), `content`, or `count` |
| `context` | number | — | Lines of context around each match |

```json
{
  "pattern": "scheduler_add",
  "path": "/home/user/claudhaus/agents",
  "type": "py",
  "output_mode": "content",
  "context": 3
}
```
```

- [ ] **Step 5: Write `site/content/api/scheduler-add.mdx`**

```mdx
---
title: scheduler_add
description: Add a recurring scheduled task.
---

Adds a task that runs on a recurring schedule. Tasks persist across restarts.

## Parameters

| Name | Type | Required | Description |
|---|---|---|---|
| `task` | string | ✓ | The prompt to run (e.g. "summarize open PRs and send_message the results") |
| `schedule_str` | string | ✓ | Human-readable schedule (see examples below) |

## Schedule examples

| `schedule_str` | When it runs |
|---|---|
| `"every 30 minutes"` | Every 30 minutes |
| `"every 2 hours"` | Every 2 hours |
| `"every day at 9am"` | Daily at 9:00 AM (server timezone) |
| `"every Monday at 8am"` | Every Monday at 8:00 AM |
| `"every weekday at 6pm"` | Mon–Fri at 6:00 PM |

## Example

```
scheduler_add(
  task="List open GitHub PRs older than 2 days and send_message a summary",
  schedule_str="every day at 9am"
)
```

## Notes

- The task prompt runs as a full Claude session — it can use any tool the agent has access to.
- Use `send_message` in the task prompt to push results to you proactively.
- Use `scheduler_list` to see task IDs, then `scheduler_remove` to cancel.
```

- [ ] **Step 6: Write `site/content/api/scheduler-list.mdx`**

```mdx
---
title: scheduler_list
description: List all scheduled tasks.
---

Returns all recurring and one-shot scheduled tasks for the current chat.

## Parameters

None.

## Returns

A list of tasks, each with:

| Field | Description |
|---|---|
| `id` | Unique task ID (used with `scheduler_remove`) |
| `task` | The task prompt |
| `schedule_str` | The human-readable schedule |
| `last_run` | When the task last ran (ISO timestamp or null) |
| `next_run` | When the task will next run |

## Example

```
scheduler_list()
```

Response:
```
Scheduled tasks (2):

ID: 7a3f  |  every day at 9am
Task: List open GitHub PRs older than 2 days and send_message a summary
Last run: 2026-04-23 09:00:02

ID: 2b1c  |  every Monday at 8am
Task: Send weekly summary of memory notes
Last run: 2026-04-21 08:00:14
```
```

- [ ] **Step 7: Write `site/content/api/scheduler-remove.mdx`**

```mdx
---
title: scheduler_remove
description: Remove a recurring scheduled task.
---

Cancels a scheduled task by its ID. Get the ID from `scheduler_list`.

## Parameters

| Name | Type | Required | Description |
|---|---|---|---|
| `task_id` | string | ✓ | Task ID from `scheduler_list` |

## Example

```
scheduler_list()
# → ID: 7a3f  |  every day at 9am

scheduler_remove(task_id="7a3f")
# → Task 7a3f removed.
```

## Notes

- One-shot tasks (`schedule_once`) expire automatically after running. Use this tool for recurring tasks only.
- Removing a task is immediate — it won't run again even if the next run was imminent.
```

- [ ] **Step 8: Write `site/content/api/schedule-once.mdx`**

```mdx
---
title: schedule_once
description: Schedule a one-shot task at a specific time.
---

Schedules a task to run once at a specified time. The task is removed after it runs.

## Parameters

| Name | Type | Required | Description |
|---|---|---|---|
| `task` | string | ✓ | The prompt to run |
| `when_str` | string | ✓ | When to run (see examples below) |

## When examples

| `when_str` | When it runs |
|---|---|
| `"in 30 minutes"` | 30 minutes from now |
| `"in 2 hours"` | 2 hours from now |
| `"at 3pm"` | Today at 3:00 PM (server timezone) |
| `"tomorrow at 9am"` | Tomorrow at 9:00 AM |

## Example

```
schedule_once(
  task="send_message('Time to review the staging deploy')",
  when_str="in 2 hours"
)
# → Scheduled for 2026-04-23 16:42:00. I'll remind you then.
```
```

- [ ] **Step 9: Write `site/content/api/subagent-list.mdx`**

```mdx
---
title: subagent_list
description: List all defined sub-agents.
---

Returns all sub-agents that have been created for this chat.

## Parameters

None.

## Returns

A list of sub-agents, each with:

| Field | Description |
|---|---|
| `name` | Unique slug identifier |
| `description` | What the sub-agent does |

## Example

```
subagent_list()
```

Response:
```
Sub-agents (2):

researcher — Searches and summarizes web content
code-reviewer — Reviews Python code for correctness and style
```
```

- [ ] **Step 10: Write `site/content/api/subagent-create.mdx`**

```mdx
---
title: subagent_create
description: Create a new focused sub-agent.
---

Defines a new sub-agent with its own system prompt and tool set. The agent is stored and can be run on demand.

## Parameters

| Name | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Slug identifier (e.g. `researcher`, `code-reviewer`) |
| `description` | string | ✓ | One-line description of what it does |
| `system_prompt` | string | ✓ | Full system prompt for the sub-agent |
| `tools` | string[] | ✓ | Tools the sub-agent can use |

## Example

```
subagent_create(
  name="researcher",
  description="Searches and summarizes web content on a given topic",
  system_prompt="You are a research specialist. Given a topic, search the web comprehensively, read the most relevant sources, and produce a structured summary with key findings and sources.",
  tools=["WebSearch", "WebFetch", "Read"]
)
```

## Notes

- Give sub-agents only the tools they need. `["WebSearch", "WebFetch"]` for a researcher, not `["*"]`.
- The system prompt starts from scratch — the sub-agent does not inherit the main agent's memory or context.
- Use `subagent_run` to execute tasks with the sub-agent.
```

- [ ] **Step 11: Write `site/content/api/subagent-run.mdx`**

```mdx
---
title: subagent_run
description: Delegate a task to a sub-agent.
---

Runs a task using a defined sub-agent and returns the result. The main agent waits for completion and incorporates the result into its response.

## Parameters

| Name | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Sub-agent name (from `subagent_list`) |
| `task` | string | ✓ | The task to perform |

## Example

```
subagent_run(
  name="researcher",
  task="Find everything published about the Claude Agent SDK in the last 30 days. Include publication dates and source URLs."
)
```

## Notes

- The task is the only context the sub-agent receives (plus its system prompt). Make it self-contained.
- Sub-agents run synchronously — the main agent waits for the result before continuing.
- For long tasks, the typing indicator remains active while the sub-agent works.
```

- [ ] **Step 12: Write `site/content/api/connector-info.mdx`**

```mdx
---
title: connector_info
description: Get required credentials for a connector.
---

Returns the credentials needed to set up a given connector, and instructions for where to get them.

## Parameters

| Name | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Connector name (e.g. `github`, `hubspot`, `slack`) |

## Example

```
connector_info(name="github")
```

Response:
```
GitHub connector requires:

GITHUB_TOKEN
  A Personal Access Token with repo, read:org scopes.
  Get one at: https://github.com/settings/tokens/new
  Select scopes: repo (full), read:org
```

## Notes

- Call this before `connector_add` to know exactly what to prepare.
- The agent calls this automatically when you say "add the GitHub connector" — you rarely need to call it directly.
```

- [ ] **Step 13: Write `site/content/api/connector-add.mdx`**

```mdx
---
title: connector_add
description: Install a connector with credentials.
---

Installs an MCP connector and restarts the bot. The connector's tools become available in the next session.

## Parameters

| Name | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Connector name (e.g. `github`, `hubspot`) |
| `credentials` | object | ✓ | Key-value pairs of required credentials |

## Example

```
connector_add(
  name="github",
  credentials={"GITHUB_TOKEN": "ghp_xxxxxxxxxxxxxxxxxxxx"}
)
```

<Warning>The bot restarts immediately after this call. Expect a 5–10 second offline period. This is normal.</Warning>

## Notes

- Get the required credential names from `connector_info` first.
- Credentials are stored encrypted in the database, not in `.env`.
- To remove a connector, tell the agent: "remove the GitHub connector."
```

- [ ] **Step 14: Write `site/content/api/share.mdx`**

```mdx
---
title: share
description: Share context with another Claudhaus user.
---

Sends a piece of context to another user. They receive a push notification and the context is injected into their next Claude session.

## Usage

```
/share @username Here's what we decided about the API — use REST not GraphQL
share with John: the staging credentials are in 1Password under "Staging DB"
```

## How it works

1. The sender's message is resolved to a target user via the user registry
2. A row is inserted into `shared_context` with `acknowledged = 0`
3. The recipient receives a push notification immediately
4. On the recipient's next message, the shared context is prepended to their Claude prompt
5. The item is marked `acknowledged = 1`

## Notes

- The target user must have previously messaged the bot (they must be in the user registry).
- If the username is ambiguous, the bot asks for clarification.
- Use `/revoke` to soft-delete shared context before the recipient's next session.
```

- [ ] **Step 15: Write `site/content/api/revoke.mdx`**

```mdx
---
title: revoke
description: Revoke shared context before it's seen.
---

Soft-deletes shared context you previously sent to another user. Prevents it from being injected into their future sessions.

## Usage

```
/revoke @username use REST not GraphQL
revoke what I shared with John about the API
```

## How it works

1. Matches the row in `shared_context` by sender + recipient + content/label fuzzy match
2. Sets `revoked = 1` (soft delete — row is kept for audit)
3. Sends the recipient a notification: "John revoked shared context: use REST not GraphQL"

## Notes

- Revocation prevents future injection and hides items from `/shared` pulls.
- Context already injected into an active Claude session is not retroactively removed — Claude has already seen it.
- You cannot revoke context on behalf of another user.
```

- [ ] **Step 16: Write `site/content/api/shared-pull.mdx`**

```mdx
---
title: shared (pull)
description: Retrieve context shared with you.
---

Displays all context that other users have shared with you, and injects it into your current Claude session.

## Usage

```
/shared
show shared context
what did Jay share with me?
anything shared from the team?
```

## How it works

1. Queries `shared_context` where `to_chat_id` matches your chat, `revoked = 0`
2. Groups results by sender, ordered by most recent first
3. Displays in chat grouped by sender with timestamps
4. Injects all items into the current Claude session
5. Marks all displayed items as `acknowledged = 1`

## Example output

```
📥 Shared with you:

From Jay (2 items)
• (Apr 22) use REST not GraphQL for the new endpoint
• (Apr 21) staging DB password is in 1Password

From Sarah (1 item)
• (Apr 20) the client wants the dashboard by May 5
```

## Notes

- Pull always shows all non-revoked items regardless of acknowledgment status.
- Items are re-injected into Claude on every pull (in case you want to reference them again).
- Push injection (on your next message after receiving a notification) is automatic and only happens once per item.
```

- [ ] **Step 17: Write `site/content/api/learn.mdx`**

```mdx
---
title: learn
description: Encode a lesson into long-term memory.
---

Writes a durable fact, rule, or preference to the appropriate memory file so it applies to all future sessions.

## Parameters

| Name | Type | Required | Description |
|---|---|---|---|
| `lesson` | string | ✓ | The fact, rule, or preference to remember |
| `category` | string | ✓ | Where to store it (see below) |
| `skill_name` | string | — | Slug for the skill file (only when `category="skill"`) |

## Categories

| Category | Written to | Use for |
|---|---|---|
| `skill` | New skill file in `skills/` | Repeatable workflows, formatting rules |
| `behavior` | `HOUSE_RULES.md` | Always/never rules about how to act |
| `preference` | `USER_PROFILE.md` | Working style, communication preferences |
| `context` | `BUSINESS_CONTEXT.md` | Business, project, team, or tech stack facts |

## Examples

```
learn(
  lesson="Always reply in short form unless the user explicitly asks for detail",
  category="preference"
)

learn(
  lesson="We use NZD for all financial figures. Never use USD.",
  category="context"
)

learn(
  lesson="Never send a Slack message without showing the user a draft first",
  category="behavior"
)

learn(
  lesson="When the user says 'morning report', pull GitHub PRs and format as...",
  category="skill",
  skill_name="morning-report"
)
```

## Notes

- The agent calls `learn` proactively — you rarely need to call it directly.
- Trigger it naturally: "remember that...", "always...", "never...", "from now on...", "I prefer..."
```

- [ ] **Step 18: Write `site/content/api/skill-tools.mdx`**

```mdx
---
title: skill_list / read / write / delete
description: Manage skills programmatically.
---

Four tools for reading and managing the agent's skill files.

---

## skill_list

Returns all skills with metadata.

**Parameters:** None.

**Returns:** List of skills with `name`, `preview` (first line), `always` (boolean), `triggers` (array).

```
skill_list()
# → morning-report  (trigger: morning report, standup)
# → code-review     (always: true)
```

---

## skill_read

Returns the full content of a skill file.

| Name | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Skill slug (from `skill_list`) |

```
skill_read(name="morning-report")
# → Returns the full Markdown content of the skill
```

---

## skill_write

Creates or overwrites a skill file. Takes effect immediately — no restart needed.

| Name | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Skill slug (e.g. `morning-report`) |
| `content` | string | ✓ | Full Markdown content of the skill |

```
skill_write(
  name="morning-report",
  content="---\nalways: false\ntriggers: [morning report, standup]\n---\n\n# Morning Report\n..."
)
```

---

## skill_delete

Removes a skill file.

| Name | Type | Required | Description |
|---|---|---|---|
| `name` | string | ✓ | Skill slug to delete |

**Returns:** `true` if deleted, `false` if not found.

```
skill_delete(name="morning-report")
# → true
```
```

- [ ] **Step 19: Build and verify all API pages**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm run build 2>&1 | tail -5
```

Expected: `Export successful`. All API reference pages in `out/api-reference/`.

- [ ] **Step 20: Commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/content/api/
git commit -m "feat(site): API reference content — all tool pages"
```

---

### Task 16: Vercel config + build verification

**Files:**
- Create: `site/.vercelignore`

- [ ] **Step 1: Create `site/.vercelignore`**

```
node_modules
.next
out
```

- [ ] **Step 2: Verify `next.config.mjs` has static export**

Open `site/next.config.mjs` and confirm it contains `output: 'export'`. No change needed if it's already there from Task 1.

- [ ] **Step 3: Run full test suite**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm test 2>&1
```

Expected: all tests pass (7 tests across mdx.test.ts and nav.test.ts).

- [ ] **Step 4: Run full production build**

```bash
cd /home/jjay/JjayFiles/claude-command-center/site
npm run build 2>&1
```

Expected: `Export successful`. No TypeScript errors. No missing module errors. `out/` directory created with all HTML files.

- [ ] **Step 5: Spot-check output**

```bash
ls /home/jjay/JjayFiles/claude-command-center/site/out/
ls /home/jjay/JjayFiles/claude-command-center/site/out/docs/
ls /home/jjay/JjayFiles/claude-command-center/site/out/api-reference/
```

Expected:
- `out/index.html` — landing page
- `out/docs/introduction.html` — docs
- `out/api-reference/overview.html` — API reference

- [ ] **Step 6: Verify Vercel deployment settings (documentation step)**

In the Vercel project dashboard:
- Root Directory: `site`
- Build Command: `npm run build` (postbuild runs Pagefind automatically)
- Output Directory: `out`
- Install Command: `npm install`

No environment variables required — site is fully static.

- [ ] **Step 7: Final commit**

```bash
cd /home/jjay/JjayFiles/claude-command-center
git add site/.vercelignore
git commit -m "feat(site): Vercel config and build verification"
```
