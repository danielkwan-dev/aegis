# Aegis frontend rebuild — design spec

**Date:** 2026-08-21
**Status:** Approved, pending implementation plan.

## Context

The Aegis backend was rebuilt earlier (see `docs/superpowers/specs/2026-08-10-aegis-rebuild-design.md` if it exists — it was lost mid-rebuild and not recovered; the project memory and git history are the record of what happened there) into a layered FastAPI service with real fine-tuned ML (DistilBERT NER, YOLOv8n vision detection), Postgres persistence, and 61 passing tests. The frontend was never touched in that pass — it's still the original YHack 2026 hackathon Next.js app: cyberpunk aesthetic (`MatrixRain`, `TypingEffect`), and critically, `HexDashboard.tsx` is still imported and rendered in `AuditResult.tsx`, hardcoded to the original author's Hex.tech embed URL. The backend's Hex.tech integration was fully removed during the backend rebuild (`analyze_threat` now runs synchronously, no external round-trip) — so that component is orphaned, receiving no real data.

This spec covers a full frontend rebuild so the whole project (backend + frontend) is genuinely deployable and portfolio/interview-ready, not just the backend half.

## Goals

- Replace the entire frontend with a new implementation against the current backend API (`/api/ingest/manual`, `/api/ingest/export`, `/api/analyze-threat`, `/api/footprint`, `/api/score-history`).
- Production-deployable: Vercel (frontend) + Render/Railway (backend + Postgres), no localhost-hardcoded assumptions.
- A clean, professional, dark security-tool visual direction — reads as serious engineering, not a hackathon demo.
- Frontend test coverage (Vitest + React Testing Library), matching the backend's testing rigor.

## Non-goals

- No landing/marketing page — the app is the whole product, single page, no separate routes.
- No auth/login system — session-cookie-scoped, single-visitor-per-browser, matching the backend's existing demo-scale design (locked in during the original backend brainstorming).
- No redesign of backend API shape — this rebuild consumes the API as it exists today; any API changes needed are called out explicitly below, not assumed.

## Required backend fix (blocking for real deployment)

The session cookie (`app/api/deps.py`) is currently set with `samesite="lax"` and no `secure` flag. That works on `localhost` (same-origin), but Vercel and Render/Railway are genuinely different domains — a `lax` cookie is **not** attached to cross-site `fetch` requests at all. Deployed as-is, every request would silently look like a brand-new session: ingestion would appear to succeed but nothing would ever persist across requests. Fix: `samesite="none", secure=True` server-side. This is a small, necessary backend change bundled into this work, not a separate project.

Backend also needs its `CORS_ORIGINS` setting to include the deployed Vercel URL in production (already configurable via existing `cors_origins` setting — no code change, just a production env var).

## Architecture

- **Next.js 14 App Router**, single page (`app/page.tsx`). `app/layout.tsx` sets up the dark theme, font, and a `QueryClientProvider` (TanStack Query). `app/globals.css` defines dark-palette design tokens consumed by both plain Tailwind classes and `shadcn/ui` components.
- **API client** (`lib/api.ts`): thin typed `fetch` wrapper. Base URL from `NEXT_PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000` in dev). Always sends `credentials: 'include'`. Distinguishes real HTTP/network failures from the backend's in-band logical-error responses (`{"status": "error"|"initializing", ...}` returned with a 200) — callers get a consistent shape either way.
- **Data layer**: TanStack Query owns all server state via hooks — `useFootprint`, `useScoreHistory`, `useIngestManual`, `useIngestExport`, `useAnalyze`. No hand-rolled `useEffect`/`useState` fetch logic.
- **Layout**: two-column console layout. Left column is persistent (ingestion controls + footprint summary). Right column is the current analysis (form + results). Not a linear wizard — a user re-analyzes repeatedly against a growing footprint, which is how the tool actually works.
- **Tech stack**: Next.js 14, TypeScript, Tailwind CSS, `shadcn/ui` (Radix primitives, component code lives in-repo), TanStack Query, Recharts (score history chart), `react-force-graph-2d` (entity graph, kept from the current frontend), Framer Motion (subtle transitions only — no theatrical effects).

## Component inventory

**Kept & rebuilt** (new implementation, not ported code):
- `EntityGraph` — force-directed graph on `react-force-graph-2d`, driven by `web.nodes`/`web.edges` from an analysis result. Restyled to the new dark palette, color-coded by node type/cluster (not neon).
- `BreachGauge` — 0–100% arc/radial gauge for `breach_probability`, color-banded by severity.

**New:**
- `IngestionPanel` — tabbed: "Manual Entry" (caption text, optional image, label) and "Import Export" (.zip upload, max-posts control).
- `FootprintSummary` — stat strip from `/api/footprint`'s `exposure_map` (posts ingested, unique streets, known locations, etc.), always visible in the left column.
- `AnalysisForm` — draft post text + optional image, submits to `/api/analyze-threat`.
- `FindingsList` — vulnerability map, grouped by severity (Critical/High/Medium/Low), each with evidence and risk-reduction-if-removed.
- `ConclusionNarrative` — the `final_conclusion` text, plain and clean, no typewriter animation.
- `ScoreHistoryChart` — Recharts line chart of `breach_probability` over time from `/api/score-history`.
- `EmptyState` — first-run guidance in the results column before any analysis has run (there's no landing page to explain this instead).
- Shared primitives from `shadcn/ui`: Button, Card, Tabs, Textarea, Badge, Skeleton, Alert, Progress.

**Removed entirely:** `HexDashboard.tsx`, `MatrixRain.tsx`, `TypingEffect.tsx`, `DigitalShadow.tsx`. `VisualizationWrapper.tsx` (a thin wrapper around `StalkerWeb`) and `SimulateForm.tsx`/`AuditResult.tsx`/`RiskGauge.tsx`/`ScoreTracker.tsx`/`StalkerWeb.tsx` are all superseded by the new component set above (new implementations, old files deleted rather than edited in place, given the scope of change).

## Data flow

1. **On load**: `useFootprint()` populates `FootprintSummary`; `useScoreHistory()` populates `ScoreHistoryChart`. An empty footprint shows a friendly "nothing ingested yet" state — not an error.
2. **Ingestion** (`useIngestManual` / `useIngestExport`): on success, invalidate the footprint query so stats refresh, and show inline confirmation (e.g., "12 posts ingested, 3 skipped" for export; "Data Point Secured" for manual).
3. **Analysis** (`useAnalyze`): on success, the mutation's result renders directly into `BreachGauge`/`FindingsList`/`ConclusionNarrative`/`EntityGraph` (not cached as a query — it's a point-in-time result, not persistent state to refetch). Also invalidates `useScoreHistory` since the backend just persisted a new history entry as a side effect of analysis.

## Error handling

- **Real HTTP/network failures** (TanStack Query's `isError`): generic "couldn't reach the server" `Alert`.
- **Backend logical-error responses** (200 status, `{"status": "error"|"initializing", ...}` body): inspected explicitly by the API client and surfaced with their actual message. `"initializing"` (no footprint yet) is informational, not a failure — must not render as an error state.
- **Free-tier cold start**: Render/Railway free tiers sleep after inactivity; first request after idle can take 20-30+ seconds. A distinct "waking up the server, this can take a minute" loading message (not a generic spinner) for requests that exceed a short threshold, so it doesn't read as broken.

## Testing

Vitest + React Testing Library. Same philosophy as the backend suite — test logic that could silently break, not markup snapshots:
- `lib/api.ts`: mocked-fetch tests for correct URL/method construction, and that both HTTP errors and in-band `{"status": "error"}` responses get surfaced consistently.
- Query/mutation hooks: `renderHook` + `QueryClientProvider` wrapper, mocked API client.
- Components with real conditional logic: `FindingsList` (severity grouping), `BreachGauge` (color banding), `IngestionPanel` (tab switching, submit wiring), empty/error/loading states.

## Deployment

- **Frontend**: Vercel. Env var: `NEXT_PUBLIC_API_BASE_URL` pointing at the deployed backend.
- **Backend**: Render or Railway, Postgres add-on. Env vars: existing `.env` set (`DATABASE_URL`, `TESSERACT_CMD`, `NER_MODEL_DIR`, `VISION_MODEL_PATH`, `SESSION_COOKIE_NAME`) plus `CORS_ORIGINS` updated to include the production Vercel URL, plus the cookie `samesite="none", secure=True` fix described above.
- Local dev is unaffected — both env vars have sensible localhost defaults, no code branches on environment beyond config values.
