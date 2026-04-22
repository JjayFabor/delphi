# Claudhaus Public Site — Design Spec

**Date:** 2026-04-23
**Status:** Approved

## Overview

A public-facing website for Claudhaus: a marketing landing page, a documentation site, and an API reference. Lives in a new `site/` folder in the same monorepo as `dashboard-ui/`. Deployed to Vercel (free tier) as a standalone Next.js app.

**Goals:**
- Convert developer visitors into self-hosters (primary CTA: Get Started)
- Build open-source credibility (secondary CTA: View on GitHub)
- Serve as the canonical documentation and API reference

**Audience:** Both technical developers who want to self-host and non-technical users evaluating the project — onboarding must feel welcoming, not intimidating.

---

## Monorepo Structure

```
claudhaus/
  dashboard-ui/     ← internal dashboard (existing, unchanged)
  site/             ← public site (new)
```

The `site/` app has no dependency on `dashboard-ui/` and no SQLite reads. Fully static.

---

## Tech Stack

| Concern | Choice |
|---|---|
| Framework | Next.js 14 (App Router) |
| Styling | Tailwind CSS |
| Content | MDX via `next-mdx-remote` + `gray-matter` |
| Code highlighting | Shiki |
| Dark/light mode | `next-themes` |
| Search | Pagefind (static, runs at build time) |
| Icons | `lucide-react` |
| Fonts | Inter (UI), JetBrains Mono (code) |
| Deploy | Vercel free tier, `output: 'export'` |

---

## File Structure

```
site/
  app/
    layout.tsx                    Root layout (theme provider, nav, footer)
    page.tsx                      Landing page
    docs/
      layout.tsx                  Docs shell (sidebar + content + TOC)
      [[...slug]]/page.tsx        MDX-driven docs pages
    api-reference/
      layout.tsx                  Same shell as docs
      [[...slug]]/page.tsx        MDX-driven API reference pages
  content/
    docs/                         MDX source files for documentation
    api/                          MDX source files for API reference
  components/
    Nav.tsx                       Top navigation bar
    Footer.tsx                    Footer
    Sidebar.tsx                   Collapsible docs sidebar
    Toc.tsx                       In-page table of contents (right rail)
    MdxComponents.tsx             Custom MDX renderers
    ThemeToggle.tsx               Dark/light toggle button
    Search.tsx                    Pagefind command palette (Cmd+K)
    Callout.tsx                   Note / Warning / Danger callout blocks
  lib/
    mdx.ts                        MDX loader (gray-matter + next-mdx-remote)
    nav.ts                        Sidebar config (ordered sections + pages)
    search.ts                     Pagefind client integration
  public/
    pagefind/                     Generated at build time
  next.config.mjs
  tailwind.config.ts
  tsconfig.json
  package.json
```

---

## Routing

| Route | Content |
|---|---|
| `/` | Landing page |
| `/docs` | Redirects to `/docs/introduction` |
| `/docs/[...slug]` | MDX file from `content/docs/` |
| `/api-reference` | Redirects to `/api-reference/overview` |
| `/api-reference/[...slug]` | MDX file from `content/api/` |

---

## Design System

### Colors

| Token | Dark | Light |
|---|---|---|
| Background | `#0A0A0F` | `#FFFFFF` |
| Surface | `#111118` | `#F8F8FC` |
| Border | `#1E1E2E` | `#E4E4EF` |
| Text primary | `#F0F0FF` | `#0A0A0F` |
| Text muted | `#6B6B8A` | `#6B6B8A` |
| Accent | `#7C6AF7` | `#5B4EE8` |
| Accent hover | `#9B8DFF` | `#7C6AF7` |
| Code background | `#0F0F1A` | `#F3F3FA` |

Dark mode is default. Light mode toggled via `next-themes`.

### Typography

- **UI / prose:** Inter (variable font, via `next/font/google`)
- **Code:** JetBrains Mono (via `next/font/google`)

### Spacing

4px base unit, Tailwind's default scale throughout.

### Component Style

Subtle `rounded-lg` corners, thin borders (`border` utility), minimal box shadows. No text gradients. Buttons use solid accent fill. Hero background has a faint radial violet glow (`#7C6AF7` at ~8% opacity) and a subtle dot-grid pattern — no other decorative elements.

---

## Landing Page

### Nav

- Left: `claudhaus` text logo
- Center: `Docs`, `API Reference`, `GitHub` links
- Right: theme toggle + `Get Started` button (accent fill)
- Sticky on scroll, backdrop blur

### Hero

**Headline:** `Your personal AI agent. Self-hosted. Claude-native.`

**Subheadline:** `Send a message from your phone. Get your own AI on the other end — shaped to your role, connected to your tools, and getting smarter every conversation.`

**Buttons:**
- Primary: `Get Started →` (accent fill, links to `/docs/introduction`)
- Secondary: `View on GitHub` (outline, links to GitHub repo)

**Below buttons:** Minimal terminal-style quick-start snippet:
```bash
git clone https://github.com/JjayFabor/claudhaus.git
cd claudhaus
python3 scripts/setup.py
```

**Background:** Faint radial violet glow behind headline. Subtle dot-grid pattern on the page background.

### Comparison Table

Headline: `How it compares`

| | Claudhaus | OpenClaw |
|---|---|---|
| Model | Claude-native (Agent SDK) | Multi-provider |
| Setup | One Python file, chat-driven | Config files + dashboard |
| Memory | BM25 search over Markdown | None built-in |
| Integrations | Self-installing MCP connectors | Config-file plugins |
| Skills | Teachable via chat, hot-loaded | Static plugins |
| Sub-agents | Spawnable via chat | Not built-in |
| Self-improvement | Edits its own source code | No |
| Target | One person, personal ops | Teams, multi-user |

Claudhaus column cells have a violet checkmark (✓) prefix. OpenClaw column is plain text.

### Feature Cards

3-column grid (collapses to 1 column on mobile). Six cards:

| Icon | Title | Description |
|---|---|---|
| `Database` | Persistent Memory | Remembers facts, preferences, and past context across every session. |
| `Pencil` | Teachable Skills | Teach new workflows just by chatting — no config files, no restarts. |
| `Plug` | MCP Connectors | Self-installing integrations: GitHub, HubSpot, Slack, and more. |
| `Bot` | Sub-agents | Spawn focused specialists with their own workspaces and tool sets. |
| `Clock` | Scheduler | Schedule recurring tasks — reports, reminders, status checks. |
| `Wrench` | Self-Improving | Main reads and edits its own source code, syntax-checks, and restarts. |

### How It Works

3-step horizontal flow (collapses to vertical on mobile):

1. **Clone & configure** — `git clone` the repo and run the setup wizard. Done in under 5 minutes.
2. **Connect your Telegram bot** — Create a bot via BotFather, paste the token. Your agent is live.
3. **Start chatting** — Name it, define its role, connect tools, and teach it your workflows — all by chatting.

### Footer

- Left: `claudhaus` text logo + tagline `Personal AI. Self-hosted.`
- Right links: `Docs`, `API Reference`, `GitHub`, `License`
- Bottom: muted text — `Independent open-source project. Not affiliated with Anthropic.`

---

## Docs Section

### Layout

Two-column shell:
- **Left:** Fixed sidebar (240px wide on desktop, drawer on mobile)
- **Center:** Scrollable MDX content (max-width prose)
- **Right:** Sticky TOC rail (hidden below `lg` breakpoint)

Same `Nav` and `Footer` as landing page.

### Sidebar Structure

```
Getting Started
  Introduction
  Prerequisites
  Quick Start
  Configuration

Core Concepts
  Memory
  Skills
  Connectors
  Sub-agents
  Scheduler

Guides
  Connecting Telegram
  Adding a Connector
  Writing a Skill
  WSL2 Setup
  Linux Setup
  macOS Setup
  Docker Setup
```

Groups are collapsible. Active page is highlighted in accent violet. All sidebar config lives in `lib/nav.ts` as an ordered array — adding a new page requires only adding an entry there and creating the MDX file.

### Docs Page Anatomy

1. Breadcrumb (`Docs / Getting Started / Quick Start`)
2. H1 title (from MDX frontmatter `title` field)
3. MDX content — prose, code blocks (Shiki), callouts
4. Previous / Next page navigation
5. Right-rail TOC with scroll-spy (highlights active heading)

### MDX Frontmatter

Every docs page has:
```yaml
---
title: Quick Start
description: Get Claudhaus running in under 5 minutes.
---
```

`title` is used for the page `<title>`, breadcrumb, sidebar label, and H1. `description` is used for `<meta name="description">`.

### Callout Components

Three variants, rendered as left-border colored blocks:

```mdx
<Note>Informational tip — blue left border</Note>
<Warning>Watch out — amber left border</Warning>
<Danger>Destructive action ahead — red left border</Danger>
```

### Search

`⌘K` / `Ctrl+K` opens a modal command palette. Pagefind indexes all MDX content at build time (`postbuild` script in `package.json`). Results show page title + matching excerpt. No external service required.

---

## API Reference Section

Same layout shell as docs (sidebar + content + TOC). Separate sidebar config in `lib/nav.ts` under an `api` key.

### Sidebar Structure

```
API Reference
  Overview
  Tools
    Bash
    Read
    Write / Edit
    Glob / Grep
  Scheduler Tools
    scheduler_add
    scheduler_list
    scheduler_remove
    schedule_once
  Sub-agent Tools
    subagent_list
    subagent_create
    subagent_run
  Connector Tools
    connector_info
    connector_add
  Shared Context Tools
    share
    revoke
    shared (pull)
  Learning Tools
    learn
    skill_list
    skill_read
    skill_write
    skill_delete
```

### API Page Anatomy

Each tool page has:
1. **Description** — what the tool does, one paragraph
2. **Parameters table** — name, type, required (✓/—), description
3. **Example** — realistic code block showing actual usage
4. **Notes** — edge cases, gotchas, constraints

---

## Vercel Deployment

- `site/` is the Vercel project root (set in Vercel project settings: `Root Directory = site`)
- Build command: `npm run build && npm run postbuild` (postbuild runs Pagefind indexer)
- Output: static export (`output: 'export'` in `next.config.mjs`)
- No environment variables required — fully static

---

## Out of Scope

- Blog or changelog page
- Authentication or user accounts
- Live data from the agent's SQLite DB
- i18n / translations
- Analytics (can be added later via Vercel Analytics)
