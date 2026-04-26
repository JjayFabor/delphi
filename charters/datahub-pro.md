# Project Charter — DataHub Pro

> **For Claude:** This file is the source of truth for DataHub Pro. Before answering anything non-trivial about this project, re-read the Living References listed in §3 — they may have changed since this charter was written. Do not assume; verify.

---

## 0. How to Bootstrap / Refresh This Charter

SSH into devbox (`ssh devbox`), then from `~/datahub-pro`:

```
Read the following and update this charter. Be honest about what you observe.
1. package.json
2. vite.config.js + src/main.js
3. src/api/index.js
4. src/composables/ — all files
5. src/views/ — all files (top-level logic only)
6. src/stores/ — all files
7. The 20 most recent git commits
8. The nginx config at /etc/nginx/sites-enabled/
```

---

## 1. Identity

- **Name:** DataHub Pro
- **One-line pitch:** B2B intelligence command center — ICP data counts, contact enrichment, saved reports, and list tooling, built on top of the Callbox DW2 data warehouse.
- **Status:** Active
- **Repo path (devbox):** `~/datahub-pro`
- **Owner:** Jaylord / Callbox Engineering
- **Charter last reviewed:** 2026-04-21

---

## 2. Repo Shape

- **Type:** Single repo — Vue 3 SPA
- **Build output:** `dist/` (Vite build) — copied to `/var/www/html/datahub-pro/` on devbox
- **Top-level structure:**
  ```
  src/
    api/          — fetch() wrappers (single file: index.js)
    assets/       — static assets
    components/   — layout/ and ui/ subdirs
    composables/  — reusable logic extracted from views
    stores/       — Pinia stores (auth, loading, sidebar, theme)
    views/        — one Vue SFC per page/route
    App.vue       — root layout (topbar + sidebar + router-view)
    main.js       — app bootstrap, router, Pinia, PrimeVue
    style.css     — global CSS variables + base styles
  dist/           — build output (don't edit directly)
  docs/plans/     — implementation plans
  ```

---

## 3. Living References (re-read each session)

| What | Where |
|---|---|
| Dependencies | `~/datahub-pro/package.json` |
| Build config / aliases | `~/datahub-pro/vite.config.js` |
| Routes + auth guards | `~/datahub-pro/src/main.js` |
| All API calls (centralized) | `~/datahub-pro/src/api/index.js` |
| API calls (composables) | `~/datahub-pro/src/composables/` |
| Auth state | `~/datahub-pro/src/stores/auth.js` |
| nginx routing + proxy config | `/etc/nginx/sites-enabled/` (on devbox) |
| ai-api relevant endpoints | See §9 — Inter-Service Contract |

---

## 4. Tech Stack

| Layer | Choice |
|---|---|
| Language | JavaScript (ES modules, no TypeScript) |
| Framework | Vue 3 (Composition API, `<script setup>`) |
| Build tool | Vite 8 |
| Routing | vue-router 5, `createWebHashHistory` (hash-based: `/#/route`) |
| State management | Pinia 3 |
| UI library | PrimeVue 4 (Aura theme) + PrimeIcons |
| CSS | Tailwind CSS 4 (Vite plugin), global CSS variables in `style.css` |
| HTTP | `fetch()` only — **axios is banned** (supply chain compromise) |
| Auth | JWT stored in `localStorage` under `dhp_token` / `dhp_role` |
| Animations | Framer Motion (installed, usage minimal) |
| Tags input | @yaireo/tagify |
| Hosting (current) | nginx on devbox — static files at `/var/www/html/datahub-pro/` |
| Hosting (planned) | Vercel — decision pending |

---

## 5. Architecture

- **Shape:** Simple SPA. No SSR, no API layer of its own — pure frontend that calls ai-api (backend).
- **Routing:** Hash-based. Base path `/datahub-pro/`. All routes prefixed with `/#/`.
- **Auth flow:**
  1. User POSTs credentials to `/datahub-pro/api/datahub/auth/login`
  2. Backend returns JWT. Stored in `localStorage` as `dhp_token`.
  3. Every API call sends `Authorization: Bearer <dhp_token>`.
  4. Router guard checks JWT expiry on every navigation. Expired → redirect to `/login`.
  5. Two roles: `admin` (all pages) and `user` (only `/saved` and `/report/:slug`).
- **Telegram linking:** When a user opens a report link from a Telegram bot (`?tgid=...`), the app fires `POST /datahub-pro/api/datahub/link-tg` to associate their tg_id with their DataHub account.
- **nginx proxy:** All `/datahub-pro/api/*` requests are proxied to `localhost:8000/api/*`. Apollo endpoint gets a 600s read timeout; all others 120s.
- **API call patterns (two exist — beware):**
  - `src/api/index.js` → BASE = `''` → calls `/api/...` (also proxied via nginx at `/datahub-pro/api/`)
  - Composables → `const API = "/datahub-pro/api"` → calls `/datahub-pro/api/...` directly
  Both work through nginx but are inconsistent. The composables pattern is preferred.
- **Data flow for a report:**
  1. `DataCount` view calls `POST /api/datamine` → gets `{ slug, totalCount, reportUrl }`
  2. User opens `/#/report/:slug`
  3. `ReportViewer` calls `useReportData` composable
  4. Composable fetches report metadata (`GET /datahub-pro/api/datahub/report/:slug`)
  5. Composable fetches paginated records (`GET .../records?page=&page_size=25`)
  6. Optional: `useCompanyBreakdown` loads company-level aggregation
  7. Optional: `useCsvExport` streams all records for CSV download

---

## 6. Conventions

- **No TypeScript** — plain `.js` and `.vue` files only
- **No axios** — `fetch()` only, explicitly enforced (comment in `src/api/index.js`)
- **Composition API only** — `<script setup>` in all SFCs
- **Composables** — business logic extracted into `src/composables/use*.js`
- **Pinia stores** — only for cross-component state (auth, theme, sidebar, loading)
- **Linting / formatting** — none configured (no ESLint, no Prettier in package.json)
- **CSS** — global variables in `style.css`; scoped `<style scoped>` per component; Tailwind for utilities
- **Naming:** views = PascalCase SFCs; composables = `use` prefix camelCase; stores = `use*Store` camelCase
- **Commits:** conventional commits style (feat/fix/refactor/chore) — observed in recent history
- **No tests** — zero test files, no test framework installed

---

## 7. Hard Rules

- **Never import axios or any HTTP client library** — `fetch()` only. This is security policy.
- **Never store JWT in sessionStorage or cookies** — `localStorage` only (current pattern, maintain consistency).
- **Never access admin routes without role check** — the router guard enforces this; don't bypass it in new routes.
- **Never add new routes without adding them to `ADMIN_ONLY` or handling the role check explicitly.**
- **Never hardcode `192.168.50.34`** in new code — this will break on Vercel. Use relative paths or env vars.
- **Never edit `dist/` directly** — it's a build artifact. Edit `src/`, rebuild.
- **Never use `createWebHistory`** — the app uses hash routing (`createWebHashHistory`). nginx is configured for this. Changing would break all deep links.

---

## 8. Known Tech Debt & Landmines

| Area | Issue | Risk |
|---|---|---|
| `src/main.js` | Duplicate comma in routes array (`{ path: '/export-log' },,`) | Low — JS tolerates it, but sloppy |
| `App.vue`, `Login.vue` | Logo URLs hardcode `http://192.168.50.34/assets/...` | **HIGH** — will 404 on Vercel. Must move to env var or public assets before deploy |
| `src/api/index.js` | BASE = `''` (different pattern from composables `API = "/datahub-pro/api"`) | Medium — both work now via nginx, but will diverge on Vercel where proxy rules differ |
| Multiple views | `<!-- TODO: wire to /api/... -->` stubs in ListCreator, ListCleaner, LinkedIn, Crawler, Settings | Low risk until those views are worked on — don't assume they're functional |
| `useReportData.js` | `saving` ref declared after `saveReport()` that references it | Low — JS hoisting handles it, but confusing to read |
| Auth | No refresh token — sessions hard-expire. User gets kicked out mid-session | Annoying UX — known, not yet addressed |
| No linting | No ESLint or Prettier configured | Gradual style drift risk |

---

## 9. Service Detail

### datahub-pro (this project — Frontend)

- **Purpose:** The user-facing web app. Runs queries, displays reports, manages saved data.
- **Stack:** Vue 3 / Vite SPA. No server-side component.
- **Don't:** Add server-side logic here. All data operations go through ai-api.

### ai-api (Backend — relevant endpoints only)

The full ai-api has many endpoints. DataHub Pro only uses these:

**Auth**
| Method | Path | Used by |
|---|---|---|
| POST | `/datahub-pro/api/datahub/auth/login` | Login.vue |
| POST | `/datahub-pro/api/datahub/link-tg` | Login.vue, App.vue (router guard) |

**Datamine / Reports**
| Method | Path | Used by |
|---|---|---|
| POST | `/api/datamine` | DataCount view via `src/api/index.js` |
| GET | `/datahub-pro/api/datahub/report/:slug` | `useReportData.loadMeta()` |
| GET | `/datahub-pro/api/datahub/report/:slug/records` | `useReportData.loadRecords()`, `useCsvExport` |
| GET | `/datahub-pro/api/datahub/report/:slug/companies` | `useCompanyBreakdown.loadCompanies()` |
| POST | `/datahub-pro/api/datahub/report/:slug/rename` | `useReportRename.saveRename()` |
| POST | `/datahub-pro/api/datamine/save/:slug` | `useReportData.saveReport()`, Saved.vue |
| POST | `/datahub-pro/api/datamine/save-breakdown/:slug` | Saved.vue |
| GET | `/datahub-pro/api/datamine/history` | Saved.vue |
| POST | `/datahub-pro/api/datamine/log-export` | `useCsvExport` |
| GET | `/datahub-pro/api/datamine/exports` | ExportLog.vue |

**Enrichment / Intelligence (wired in api/index.js — views may be stubs)**
| Method | Path | Status |
|---|---|---|
| POST | `/api/apollo/search-with-dedup` | Wired |
| POST | `/api/lusha/enrich` | Wired |
| POST | `/api/gemini/extract-icp` | Wired |
| POST | `/api/crawler` | Wired |
| POST | `/api/report-token/generate` | Wired |
| POST | `/api/report-token/validate` | Wired |

**Auth header format:** `Authorization: Bearer <dhp_token>` (JWT issued by ai-api `/datahub/auth/login`)

---

## 10. How to Run

> All commands run on **devbox (192.168.50.34)** via SSH. This is not a local project.

```bash
ssh devbox
cd ~/datahub-pro
```

**Development (Vite dev server):**
```bash
npm run dev        # starts on http://localhost:5173/datahub-pro/
```
Note: API calls will still proxy through nginx (nginx listens on 443 → :8000). The dev server is for hot-reload only.

**Build + Deploy to nginx:**
```bash
npm run build                                          # outputs to dist/
cp -r dist/* /var/www/html/datahub-pro/               # deploy to nginx root
```

**Live URL:** `https://192.168.50.34/datahub-pro/`

**nginx:** Already running (`pgrep nginx`). Config at `/etc/nginx/sites-enabled/`. Restart: `sudo nginx -s reload`

**Deployment (planned — Vercel):** TBD. Will require:
- Removing hardcoded `192.168.50.34` references
- Configuring Vite env vars for API base URL
- Vercel rewrites for `/#/` hash routing (likely no config needed — hash routing is client-side)
- API proxy rules (replaces nginx's `/datahub-pro/api/` → `:8000` proxy)

---

## 11. How I Want Claude to Work on This Project

- **Default style:** Concise. No preamble.
- **Code output:** Targeted edits (show only the changed function/block), not full file rewrites — unless the file is small.
- **When unsure:** Proceed with best judgment, flag assumptions at the end.
- **Always do:** Check if the change touches the API call pattern (see §5 — two patterns exist). Note which one is being used.
- **Never do:** Don't suggest axios or any HTTP library. Don't add TypeScript. Don't change hash routing to history routing without explicit instruction.
- **Push back when:** A change would hardcode the devbox IP, bypass the router auth guard, or touch `dist/` directly.

---

## 11.5. Commit & PR Conventions

- **Format:** Conventional commits — `type(scope): message`
  - Types: `feat`, `fix`, `refactor`, `chore`, `docs`
  - Scope: view name or composable name (e.g. `feat(ReportViewer):`, `fix(useReportData):`)
- **Branch:** Feature branches off `main`. Direct push to main is used for small fixes (observed in history).
- **No PR process** currently — direct commits to main.
- **No `Co-Authored-By` attribution** in commits.

---

## 12. Open Questions

- When is Vercel deployment happening? (Blocks hardcoded IP cleanup and API base URL refactor)
- Will TypeScript ever be added? (Affects all future composable design)
- Is there a staging environment, or is devbox the only one?
- `src/api/index.js` vs composable API pattern — which one wins long-term? Should index.js be deprecated?
- Several views are stubs (ListCreator, ListCleaner, LinkedIn, Crawler) — are these in scope for the next sprint?
