# Aegis Frontend Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hackathon-era Next.js frontend (including the orphaned `HexDashboard.tsx`) with a production-deployable app against the current backend API, using `shadcn/ui` + TanStack Query + Recharts, with Vitest/RTL test coverage.

**Architecture:** Single-page (no separate landing route) two-column console layout: a persistent left column (footprint summary, ingestion, score history) and a right column (analysis form + results). All server state flows through TanStack Query hooks calling a thin typed `fetch` wrapper (`lib/api.ts`). One small backend fix (session cookie `samesite`/`secure`) is bundled in since it blocks real cross-origin deployment.

**Tech Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS v4, `shadcn/ui`, `@tanstack/react-query`, `recharts`, `react-force-graph-2d`, Vitest + React Testing Library.

**Spec:** `docs/superpowers/specs/2026-08-21-frontend-rebuild-design.md`

## Global Constraints

- No landing page — single app route at `frontend/app/page.tsx`.
- No auth/login — session-cookie-scoped, matching the existing backend design.
- `credentials: 'include'` on every API call — the session cookie is how the backend scopes data per visitor.
- Every component's data comes through a TanStack Query hook — no ad hoc `useEffect`/`fetch` in components.
- Dark theme only, `shadcn/ui` "new-york" style, no neon/cyberpunk styling (dropped: `MatrixRain`, `TypingEffect`, `DigitalShadow`, `HexDashboard`, `VisualizationWrapper`, and the current `SimulateForm`/`AuditResult`/`RiskGauge`/`ScoreTracker`/`StalkerWeb`, all superseded).
- Test philosophy: cover real conditional/branching logic (severity grouping, error-state handling, data transforms) — skip tests for components with no logic (`ConclusionNarrative`, `EmptyState`).
- All new frontend commands run from the `frontend/` directory; all new backend commands run from `backend/` with `venv/Scripts/python.exe`.

---

## File structure

```
backend/
  app/api/deps.py                    # MODIFY — cookie samesite/secure fix
  tests/test_session_cookie.py       # CREATE

frontend/
  components.json                    # CREATE — shadcn config
  vitest.config.ts                   # CREATE
  vitest.setup.ts                    # CREATE
  .env.example                       # CREATE
  lib/
    utils.ts                         # CREATE (shadcn init generates this)
    api-types.ts                     # CREATE
    api.ts                           # CREATE
    api.test.ts                      # CREATE
    test-utils.tsx                   # CREATE
    hooks/
      use-footprint.ts                # CREATE
      use-footprint.test.tsx          # CREATE
      use-score-history.ts            # CREATE
      use-score-history.test.tsx      # CREATE
      use-ingest.ts                   # CREATE
      use-ingest.test.tsx             # CREATE
      use-analyze.ts                  # CREATE
      use-analyze.test.tsx            # CREATE
  components/
    ui/                               # CREATE — shadcn-generated primitives
    providers.tsx                     # CREATE
    footprint-summary.tsx             # CREATE
    footprint-summary.test.tsx        # CREATE
    ingestion-panel.tsx               # CREATE
    ingestion-panel.test.tsx          # CREATE
    analysis-form.tsx                 # CREATE
    analysis-form.test.tsx            # CREATE
    breach-gauge.tsx                  # CREATE
    breach-gauge.test.tsx             # CREATE
    findings-list.tsx                 # CREATE
    findings-list.test.tsx            # CREATE
    conclusion-narrative.tsx          # CREATE (no test — no branching logic)
    empty-state.tsx                   # CREATE (no test — no branching logic)
    score-history-chart.tsx           # CREATE
    score-history-chart.test.tsx      # CREATE
    entity-graph.tsx                  # CREATE
    entity-graph.test.tsx             # CREATE
    HexDashboard.tsx                  # DELETE
    MatrixRain.tsx                    # DELETE
    TypingEffect.tsx                  # DELETE
    DigitalShadow.tsx                 # DELETE
    VisualizationWrapper.tsx          # DELETE
    SimulateForm.tsx                  # DELETE
    AuditResult.tsx                   # DELETE
    RiskGauge.tsx                     # DELETE
    ScoreTracker.tsx                  # DELETE
    StalkerWeb.tsx                    # DELETE
  app/
    layout.tsx                        # MODIFY
    page.tsx                          # MODIFY
    globals.css                       # MODIFY

README.md                             # MODIFY — deployment instructions
```

---

### Task 1: Backend — fix session cookie for cross-origin deployment

**Files:**
- Modify: `backend/app/api/deps.py`
- Test: `backend/tests/test_session_cookie.py`

**Interfaces:**
- Produces: no interface change — `get_session_id(request, response) -> str` keeps its signature; only the `Set-Cookie` attributes change.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_session_cookie.py`:

```python
from fastapi import Response
from starlette.requests import Request

from app.api.deps import get_session_id


def _request_without_cookie() -> Request:
    return Request({"type": "http", "headers": []})


def test_session_cookie_allows_cross_site_requests():
    request = _request_without_cookie()
    response = Response()

    get_session_id(request, response)

    set_cookie = response.headers.get("set-cookie", "")
    assert "samesite=none" in set_cookie.lower()
    assert "secure" in set_cookie.lower()


def test_existing_cookie_is_reused_without_setting_a_new_one():
    request = Request({"type": "http", "headers": [(b"cookie", b"aegis_session_id=abc123")]})
    response = Response()

    session_id = get_session_id(request, response)

    assert session_id == "abc123"
    assert "set-cookie" not in response.headers
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && venv/Scripts/python.exe -m pytest tests/test_session_cookie.py -v`
Expected: `test_session_cookie_allows_cross_site_requests` FAILs (current cookie is `samesite=lax`, no `secure` flag). `test_existing_cookie_is_reused_without_setting_a_new_one` should already PASS (it's exercising existing behavior) — that's fine, it's there to lock in the no-op-when-cookie-exists path so the fix below doesn't accidentally break it.

- [ ] **Step 3: Fix the cookie attributes**

In `backend/app/api/deps.py`, change the `response.set_cookie(...)` call:

```python
def get_session_id(request: Request, response: Response) -> str:
    """Read the visitor's session cookie, creating one if it's missing.

    No auth system by design (demo-scale, single-visitor-per-browser is
    enough) — this is just what scopes one visitor's footprint data from
    everyone else's in the shared Postgres tables.

    samesite="none" + secure=True (not "lax") because the frontend and
    backend are deployed on different domains (Vercel / Render-Railway) —
    a "lax" cookie is never attached to cross-site fetch() calls at all,
    which would silently make every request look like a brand-new session.
    """
    settings = get_settings()
    cookie_name = settings.session_cookie_name
    session_id = request.cookies.get(cookie_name)
    if not session_id:
        session_id = uuid.uuid4().hex
        response.set_cookie(
            cookie_name,
            session_id,
            httponly=True,
            samesite="none",
            secure=True,
            max_age=60 * 60 * 24 * 30,
        )
    return session_id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && venv/Scripts/python.exe -m pytest tests/test_session_cookie.py -v`
Expected: both PASS.

- [ ] **Step 5: Run the full backend suite to confirm no regressions**

Run: `cd backend && venv/Scripts/python.exe -m pytest tests/ -q`
Expected: all pass (62 tests — 61 existing + 1 new file with 2 tests, net +1 since this replaces nothing).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/deps.py backend/tests/test_session_cookie.py
git commit -m "Fix session cookie for cross-origin deployment (samesite=none, secure=True)"
```

---

### Task 2: Frontend — dependencies, Vitest, shadcn/ui, dark theme tokens

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/vitest.setup.ts`
- Create: `frontend/components.json` (generated by shadcn CLI)
- Create: `frontend/lib/utils.ts` (generated by shadcn CLI)
- Create: `frontend/components/ui/{button,card,tabs,textarea,badge,skeleton,alert,progress}.tsx` (generated by shadcn CLI)
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Produces: `cn()` from `@/lib/utils` (used by every component task below), `shadcn/ui` primitives under `@/components/ui/*`, Tailwind utility classes `text-severity-critical` / `text-severity-high` / `text-severity-medium` / `text-severity-low` (and their `bg-`/`border-`/`stroke-` variants) from the new `@theme` tokens.

- [ ] **Step 1: Install data/chart/testing dependencies**

Run from `frontend/`:
```bash
npm install @tanstack/react-query recharts
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

- [ ] **Step 2: Initialize shadcn/ui**

Run from `frontend/`:
```bash
npx shadcn@latest init -d -y
```
This detects the existing Tailwind v4 + `@theme` setup in `app/globals.css`, creates `components.json` and `lib/utils.ts`, and adds its own required dependencies (`clsx`, `tailwind-merge`, `class-variance-authority`, `lucide-react`) to `package.json` automatically.

- [ ] **Step 3: Add the shadcn/ui primitives this rebuild needs**

Run from `frontend/`:
```bash
npx shadcn@latest add button card tabs textarea badge skeleton alert progress
```

- [ ] **Step 4: Verify the generated files exist**

Run: `ls frontend/components.json frontend/lib/utils.ts frontend/components/ui/button.tsx frontend/components/ui/card.tsx frontend/components/ui/tabs.tsx frontend/components/ui/textarea.tsx frontend/components/ui/badge.tsx frontend/components/ui/skeleton.tsx frontend/components/ui/alert.tsx frontend/components/ui/progress.tsx`
Expected: all listed files exist (no "No such file" errors).

- [ ] **Step 5: Append severity-color design tokens to globals.css**

Append this block to the end of `frontend/app/globals.css` (after whatever `init` generated above it — do not remove the generated `@theme`/`:root`/`.dark` blocks):

```css
/* ── Aegis severity palette (additive to the shadcn base theme) ── */
@theme {
  --color-severity-critical: oklch(0.58 0.22 25);
  --color-severity-high: oklch(0.68 0.19 45);
  --color-severity-medium: oklch(0.78 0.15 85);
  --color-severity-low: oklch(0.65 0.03 240);
}
```

- [ ] **Step 6: Add test scripts to package.json**

In `frontend/package.json`, add to `"scripts"`:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 7: Create the Vitest config**

Create `frontend/vitest.config.ts`:

```typescript
import path from "path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    globals: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
```

- [ ] **Step 8: Create the Vitest setup file**

Create `frontend/vitest.setup.ts`:

```typescript
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 9: Verify the test runner itself works**

Create a throwaway smoke test to confirm the harness is wired correctly, run it, then delete it:
```bash
cat > frontend/lib/_smoke.test.ts << 'EOF'
import { describe, expect, it } from "vitest";
describe("smoke", () => { it("runs", () => { expect(1 + 1).toBe(2); }); });
EOF
cd frontend && npm test
rm frontend/lib/_smoke.test.ts
```
Expected: 1 test passes before deleting the smoke file.

- [ ] **Step 10: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/components.json frontend/lib/utils.ts frontend/components/ui frontend/vitest.config.ts frontend/vitest.setup.ts frontend/app/globals.css
git commit -m "Set up shadcn/ui, TanStack Query deps, Vitest, and severity theme tokens"
```

---

### Task 3: Frontend — shared API types

**Files:**
- Create: `frontend/lib/api-types.ts`

**Interfaces:**
- Produces: every type below, imported by `lib/api.ts` (Task 4) and every component task.

- [ ] **Step 1: Write the types**

Create `frontend/lib/api-types.ts`:

```typescript
export interface DetectedEntities {
  streets: string[];
  places: string[];
  businesses: string[];
  times: string[];
  coordinates: { lat: number; lon: number }[];
}

export interface VulnerabilityFinding {
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  finding: string;
  evidence_count: number;
}

export interface StaticLandmark {
  type: "street" | "coordinates";
  value: string | { lat: number; lon: number } | { noise_count: number };
  appearances: number;
  percentage: number;
  classification: string;
  signal?: "routine_exposure" | "anomalous_disclosure";
}

export interface EntityTriplet {
  location: string;
  time: string | null;
  day: string | null;
  activity: string | null;
  entry_count: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  color: string;
  detail?: string;
  similarity?: number;
  percentage?: number;
  classification?: string;
  cluster_id?: number | null;
  cluster_name?: string | null;
  [key: string]: unknown;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
  label: string;
}

export interface ExposureMap {
  total_data_points: number;
  unique_streets: number;
  known_locations: number;
  unique_businesses: number;
  tracked_activities: number;
  day_patterns: number;
}

export interface TimeContext {
  source: "exif" | "text_keyword";
  period: string;
  day_of_week?: string;
  hour?: number;
  datetime?: string;
  keyword?: string;
  window?: string;
}

export interface AnalysisSignals {
  draft_text_length: number;
  ocr_text: string | null;
  ocr_high_value: unknown[] | null;
  exif_metadata: Record<string, unknown> | null;
  time_context: TimeContext | null;
  merged_length: number;
}

export interface ClusterSummary {
  id: number;
  name: string;
  size: number;
  risk_score: number;
  top_terms: string[];
  is_target: boolean;
}

export interface ClusteringResult {
  n_clusters: number;
  draft_cluster_id: number;
  draft_cluster_name: string;
  draft_hits_target: boolean;
  cluster_confidence: number;
  clusters: ClusterSummary[];
}

export interface AnalyzeThreatEmpty {
  status: "empty";
  message: string;
  web: { nodes: GraphNode[]; edges: GraphEdge[] };
  exposure_map: ExposureMap;
}

export interface AnalyzeThreatInitializing {
  status: "initializing";
  message: string;
  detected_entities: DetectedEntities;
  vulnerability_map: VulnerabilityFinding[];
  breach_probability: number;
  final_conclusion: string;
  web: { nodes: GraphNode[]; edges: GraphEdge[] };
  exposure_map: ExposureMap;
}

export interface AnalyzeThreatAnalyzed {
  status: "analyzed";
  detected_entities: DetectedEntities;
  category_similarity: Record<string, number>;
  breach_probability: number;
  vulnerability_map: VulnerabilityFinding[];
  static_landmarks: StaticLandmark[];
  entity_triplets: EntityTriplet[];
  final_conclusion: string;
  signals: AnalysisSignals;
  web: { nodes: GraphNode[]; edges: GraphEdge[] };
  exposure_map: ExposureMap;
  clustering?: ClusteringResult;
}

export type AnalyzeThreatResult =
  | AnalyzeThreatEmpty
  | AnalyzeThreatInitializing
  | AnalyzeThreatAnalyzed;

export interface FootprintEntryDict {
  id: string;
  label: string;
  text: string;
  entities: DetectedEntities;
  metadata: Record<string, unknown>;
  time_context: TimeContext | null;
  has_gps: boolean;
  ingested_at: string;
}

export interface FootprintResponse {
  exposure_map: ExposureMap;
  entries: FootprintEntryDict[];
}

export interface IngestManualEmpty {
  status: "empty";
  message: string;
}

export interface IngestManualSecured {
  status: "secured";
  message: string;
  entry: FootprintEntryDict;
  detected_entities: DetectedEntities;
  exposure_map: ExposureMap;
  final_conclusion: string;
}

export type IngestManualResult = IngestManualEmpty | IngestManualSecured;

export interface IngestExportSynced {
  status: "synced";
  posts_available: number;
  posts_ingested: number;
  posts_skipped: number;
  exposure_map: ExposureMap;
}

export interface IngestExportError {
  status: "error";
  message: string;
}

export type IngestExportResult = IngestExportSynced | IngestExportError;

export interface ScoreHistoryEntryDict {
  timestamp: string;
  breach_probability: number;
  severity_counts: Record<"critical" | "high" | "medium" | "low", number>;
  entity_counts: Record<string, number>;
}

export interface ScoreHistoryResponse {
  history: ScoreHistoryEntryDict[];
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors referencing `api-types.ts` (errors from not-yet-written files that reference it are fine at this point in the plan — there are none yet, since nothing imports it).

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api-types.ts
git commit -m "Add shared TypeScript types mirroring the backend API response shapes"
```

---

### Task 4: Frontend — API client

**Files:**
- Create: `frontend/lib/api.ts`
- Test: `frontend/lib/api.test.ts`

**Interfaces:**
- Consumes: types from `frontend/lib/api-types.ts` (Task 3).
- Produces: `fetchFootprint()`, `fetchScoreHistory()`, `ingestManual(formData)`, `ingestExport(formData)`, `analyzeThreat(formData)` — all `Promise`-returning, all thrown errors are instances of `ApiError`. Consumed by the query hooks in Task 5.

- [ ] **Step 1: Write the failing tests**

Create `frontend/lib/api.test.ts`:

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, analyzeThreat, fetchFootprint, ingestExport, ingestManual } from "./api";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("fetches footprint with credentials included", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ exposure_map: { total_data_points: 0 }, entries: [] }),
    });
    vi.stubGlobal("fetch", mockFetch);

    await fetchFootprint();

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/footprint"),
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("throws ApiError on a network failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );

    await expect(fetchFootprint()).rejects.toBeInstanceOf(ApiError);
  });

  it("throws ApiError on a non-2xx HTTP response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }),
    );

    await expect(fetchFootprint()).rejects.toBeInstanceOf(ApiError);
  });

  it("resolves with the parsed body for an in-band logical error (still HTTP 200)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "error", message: "bad zip file" }),
      }),
    );

    const formData = new FormData();
    const result = await ingestExport(formData);

    expect(result).toEqual({ status: "error", message: "bad zip file" });
  });

  it("posts FormData as the body for mutations", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "empty", message: "No data to ingest." }),
    });
    vi.stubGlobal("fetch", mockFetch);

    const formData = new FormData();
    formData.set("text", "hello");
    await ingestManual(formData);

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/ingest/manual"),
      expect.objectContaining({ method: "POST", body: formData }),
    );
  });

  it("analyzeThreat posts to /api/analyze-threat", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "empty", message: "No text or image data to analyze.", web: { nodes: [], edges: [] }, exposure_map: { total_data_points: 0 } }),
    });
    vi.stubGlobal("fetch", mockFetch);

    await analyzeThreat(new FormData());

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/analyze-threat"),
      expect.objectContaining({ method: "POST" }),
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run lib/api.test.ts`
Expected: FAIL — `./api` module doesn't exist yet.

- [ ] **Step 3: Implement the API client**

Create `frontend/lib/api.ts`:

```typescript
import type {
  AnalyzeThreatResult,
  FootprintResponse,
  IngestExportResult,
  IngestManualResult,
  ScoreHistoryResponse,
} from "./api-types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      credentials: "include",
    });
  } catch {
    throw new ApiError(
      "Couldn't reach the server. Check your connection and that the backend is running.",
    );
  }

  if (!response.ok) {
    throw new ApiError(`Server returned an unexpected error (${response.status}).`);
  }

  return (await response.json()) as T;
}

export function fetchFootprint(): Promise<FootprintResponse> {
  return request<FootprintResponse>("/api/footprint");
}

export function fetchScoreHistory(): Promise<ScoreHistoryResponse> {
  return request<ScoreHistoryResponse>("/api/score-history");
}

export function ingestManual(formData: FormData): Promise<IngestManualResult> {
  return request<IngestManualResult>("/api/ingest/manual", {
    method: "POST",
    body: formData,
  });
}

export function ingestExport(formData: FormData): Promise<IngestExportResult> {
  return request<IngestExportResult>("/api/ingest/export", {
    method: "POST",
    body: formData,
  });
}

export function analyzeThreat(formData: FormData): Promise<AnalyzeThreatResult> {
  return request<AnalyzeThreatResult>("/api/analyze-threat", {
    method: "POST",
    body: formData,
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run lib/api.test.ts`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/api.test.ts
git commit -m "Add typed API client wrapping fetch for the backend endpoints"
```

---

### Task 5: Frontend — test utility for query-hook/component tests

**Files:**
- Create: `frontend/lib/test-utils.tsx`

**Interfaces:**
- Produces: `renderWithQueryClient(ui)` — used by every hook and component test from Task 6 onward.

- [ ] **Step 1: Write it directly (no test needed — this is test infrastructure itself)**

Create `frontend/lib/test-utils.tsx`:

```tsx
import type { ReactElement, ReactNode } from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function Wrapper({ children }: { children: ReactNode }) {
  const client = createTestQueryClient();
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

export function renderWithQueryClient(ui: ReactElement) {
  return render(ui, { wrapper: Wrapper });
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/test-utils.tsx
git commit -m "Add QueryClient test wrapper utility for hook/component tests"
```

---

### Task 6: Frontend — query hooks (footprint, score history)

**Files:**
- Create: `frontend/lib/hooks/use-footprint.ts`
- Create: `frontend/lib/hooks/use-footprint.test.tsx`
- Create: `frontend/lib/hooks/use-score-history.ts`
- Create: `frontend/lib/hooks/use-score-history.test.tsx`

**Interfaces:**
- Consumes: `fetchFootprint`, `fetchScoreHistory` from `lib/api.ts` (Task 4); `renderWithQueryClient` from `lib/test-utils.tsx` (Task 5) is not directly usable for hooks (needs `renderHook`) — tests below wrap `renderHook` with the same `QueryClientProvider` pattern inline.
- Produces: `useFootprint()`, `useScoreHistory()` — both return a TanStack Query `UseQueryResult`. Consumed by `FootprintSummary` (Task 8) and `ScoreHistoryChart` (Task 12).

- [ ] **Step 1: Write the failing tests**

Create `frontend/lib/hooks/use-footprint.test.tsx`:

```typescript
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { useFootprint } from "./use-footprint";
import * as api from "@/lib/api";

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("useFootprint", () => {
  it("returns footprint data on success", async () => {
    vi.spyOn(api, "fetchFootprint").mockResolvedValue({
      exposure_map: {
        total_data_points: 3,
        unique_streets: 1,
        known_locations: 0,
        unique_businesses: 0,
        tracked_activities: 0,
        day_patterns: 0,
      },
      entries: [],
    });

    const { result } = renderHook(() => useFootprint(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.exposure_map.total_data_points).toBe(3);
  });
});
```

Create `frontend/lib/hooks/use-score-history.test.tsx`:

```typescript
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { useScoreHistory } from "./use-score-history";
import * as api from "@/lib/api";

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("useScoreHistory", () => {
  it("returns score history data on success", async () => {
    vi.spyOn(api, "fetchScoreHistory").mockResolvedValue({
      history: [
        {
          timestamp: "2026-08-21T00:00:00Z",
          breach_probability: 42,
          severity_counts: { critical: 0, high: 1, medium: 0, low: 0 },
          entity_counts: {},
        },
      ],
    });

    const { result } = renderHook(() => useScoreHistory(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.history).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run lib/hooks/use-footprint.test.tsx lib/hooks/use-score-history.test.tsx`
Expected: FAIL — hook modules don't exist yet.

- [ ] **Step 3: Implement the hooks**

Create `frontend/lib/hooks/use-footprint.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchFootprint } from "@/lib/api";

export function useFootprint() {
  return useQuery({
    queryKey: ["footprint"],
    queryFn: fetchFootprint,
  });
}
```

Create `frontend/lib/hooks/use-score-history.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchScoreHistory } from "@/lib/api";

export function useScoreHistory() {
  return useQuery({
    queryKey: ["score-history"],
    queryFn: fetchScoreHistory,
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run lib/hooks/use-footprint.test.tsx lib/hooks/use-score-history.test.tsx`
Expected: both PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/hooks/use-footprint.ts frontend/lib/hooks/use-footprint.test.tsx frontend/lib/hooks/use-score-history.ts frontend/lib/hooks/use-score-history.test.tsx
git commit -m "Add footprint and score-history query hooks"
```

---

### Task 7: Frontend — mutation hooks (ingest, analyze)

**Files:**
- Create: `frontend/lib/hooks/use-ingest.ts`
- Create: `frontend/lib/hooks/use-ingest.test.tsx`
- Create: `frontend/lib/hooks/use-analyze.ts`
- Create: `frontend/lib/hooks/use-analyze.test.tsx`

**Interfaces:**
- Consumes: `ingestManual`, `ingestExport`, `analyzeThreat` from `lib/api.ts` (Task 4).
- Produces: `useIngestManual()`, `useIngestExport()`, `useAnalyze()` — all `UseMutationResult`. Consumed by `IngestionPanel` (Task 9) and `AnalysisForm` (Task 10).

- [ ] **Step 1: Write the failing tests**

Create `frontend/lib/hooks/use-ingest.test.tsx`:

```typescript
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { useIngestExport, useIngestManual } from "./use-ingest";
import * as api from "@/lib/api";

function makeWrapper() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const invalidateSpy = vi.spyOn(client, "invalidateQueries");
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { wrapper, invalidateSpy };
}

describe("useIngestManual", () => {
  it("invalidates the footprint query on success", async () => {
    vi.spyOn(api, "ingestManual").mockResolvedValue({
      status: "secured",
      message: "Data Point Secured",
      entry: {} as never,
      detected_entities: { streets: [], places: [], businesses: [], times: [], coordinates: [] },
      exposure_map: {
        total_data_points: 1, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
      final_conclusion: "",
    });
    const { wrapper, invalidateSpy } = makeWrapper();

    const { result } = renderHook(() => useIngestManual(), { wrapper });
    act(() => { result.current.mutate(new FormData()); });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["footprint"] });
  });
});

describe("useIngestExport", () => {
  it("invalidates the footprint query on success", async () => {
    vi.spyOn(api, "ingestExport").mockResolvedValue({
      status: "synced",
      posts_available: 5,
      posts_ingested: 5,
      posts_skipped: 0,
      exposure_map: {
        total_data_points: 5, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
    });
    const { wrapper, invalidateSpy } = makeWrapper();

    const { result } = renderHook(() => useIngestExport(), { wrapper });
    act(() => { result.current.mutate(new FormData()); });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["footprint"] });
  });
});
```

Create `frontend/lib/hooks/use-analyze.test.tsx`:

```typescript
import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { useAnalyze } from "./use-analyze";
import * as api from "@/lib/api";

describe("useAnalyze", () => {
  it("invalidates score-history on success", async () => {
    vi.spyOn(api, "analyzeThreat").mockResolvedValue({
      status: "empty",
      message: "No text or image data to analyze.",
      web: { nodes: [], edges: [] },
      exposure_map: {
        total_data_points: 0, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    const invalidateSpy = vi.spyOn(client, "invalidateQueries");
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useAnalyze(), { wrapper });
    act(() => { result.current.mutate(new FormData()); });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["score-history"] });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run lib/hooks/use-ingest.test.tsx lib/hooks/use-analyze.test.tsx`
Expected: FAIL — hook modules don't exist yet.

- [ ] **Step 3: Implement the hooks**

Create `frontend/lib/hooks/use-ingest.ts`:

```typescript
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ingestExport, ingestManual } from "@/lib/api";

export function useIngestManual() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ingestManual,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["footprint"] });
    },
  });
}

export function useIngestExport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ingestExport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["footprint"] });
    },
  });
}
```

Create `frontend/lib/hooks/use-analyze.ts`:

```typescript
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { analyzeThreat } from "@/lib/api";

export function useAnalyze() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: analyzeThreat,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["score-history"] });
    },
  });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run lib/hooks/use-ingest.test.tsx lib/hooks/use-analyze.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/hooks/use-ingest.ts frontend/lib/hooks/use-ingest.test.tsx frontend/lib/hooks/use-analyze.ts frontend/lib/hooks/use-analyze.test.tsx
git commit -m "Add ingest and analyze mutation hooks"
```

---

### Task 8: Frontend — QueryClientProvider wiring and root layout

**Files:**
- Create: `frontend/components/providers.tsx`
- Modify: `frontend/app/layout.tsx`

**Interfaces:**
- Consumes: `@tanstack/react-query`.
- Produces: `<Providers>` wrapping the app in `layout.tsx` — everything from Task 6/7's hooks onward needs this to be mounted to function in the real app (tests use their own wrapper, so this doesn't block earlier tasks' tests).

- [ ] **Step 1: Create the Providers component**

Create `frontend/components/providers.tsx`:

```tsx
"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            staleTime: 30_000,
          },
        },
      }),
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

- [ ] **Step 2: Replace the root layout**

Replace the full contents of `frontend/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: "Aegis | Privacy Intelligence Engine",
  description:
    "Detects Identity Links -- cross-post patterns of location, time, and activity that reveal a daily routine from public social media alone.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

**Post-Task-2 addendum:** `className="dark"` on `<html>` was added after Task 2's review found that shadcn's generated `globals.css` ships a light `:root` with dark values gated behind a `.dark` class — without this, every `shadcn/ui` primitive from Task 2 onward would render in light mode, violating the Global Constraint "Dark theme only." This is the fix for that.

- [ ] **Step 3: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors (the old `MatrixRain` import is gone; `MatrixRain.tsx` itself is deleted in Task 17, so no dangling reference remains after that task — until then it's just an unused file, not a compile error).

- [ ] **Step 4: Commit**

```bash
git add frontend/components/providers.tsx frontend/app/layout.tsx
git commit -m "Wire up TanStack QueryClientProvider, drop MatrixRain from the root layout"
```

---

### Task 9: Frontend — FootprintSummary

**Files:**
- Create: `frontend/components/footprint-summary.tsx`
- Test: `frontend/components/footprint-summary.test.tsx`

**Interfaces:**
- Consumes: `useFootprint` (Task 6), `renderWithQueryClient` (Task 5), `Card`/`CardHeader`/`CardTitle`/`CardContent`/`Skeleton` from `@/components/ui/*` (Task 2).
- Produces: `<FootprintSummary />`, used by `app/page.tsx` (Task 17).

- [ ] **Step 1: Write the failing tests**

Create `frontend/components/footprint-summary.test.tsx`:

```tsx
import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { FootprintSummary } from "./footprint-summary";
import { renderWithQueryClient } from "@/lib/test-utils";
import * as api from "@/lib/api";

describe("FootprintSummary", () => {
  it("renders exposure map stats once loaded", async () => {
    vi.spyOn(api, "fetchFootprint").mockResolvedValue({
      exposure_map: {
        total_data_points: 7,
        unique_streets: 2,
        known_locations: 1,
        unique_businesses: 3,
        tracked_activities: 4,
        day_patterns: 1,
      },
      entries: [],
    });

    renderWithQueryClient(<FootprintSummary />);

    await waitFor(() => expect(screen.getByText("7")).toBeInTheDocument());
    expect(screen.getByText(/unique streets/i)).toBeInTheDocument();
  });

  it("shows a nothing-ingested hint when the footprint is empty", async () => {
    vi.spyOn(api, "fetchFootprint").mockResolvedValue({
      exposure_map: {
        total_data_points: 0, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
      entries: [],
    });

    renderWithQueryClient(<FootprintSummary />);

    await waitFor(() =>
      expect(screen.getByText(/nothing ingested yet/i)).toBeInTheDocument(),
    );
  });

  it("shows an error message if the query fails", async () => {
    vi.spyOn(api, "fetchFootprint").mockRejectedValue(new Error("network down"));

    renderWithQueryClient(<FootprintSummary />);

    await waitFor(() =>
      expect(screen.getByText(/couldn't load footprint/i)).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run components/footprint-summary.test.tsx`
Expected: FAIL — component doesn't exist yet.

- [ ] **Step 3: Implement the component**

Create `frontend/components/footprint-summary.tsx`:

```tsx
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useFootprint } from "@/lib/hooks/use-footprint";
import type { ExposureMap } from "@/lib/api-types";

const STATS: { key: keyof ExposureMap; label: string }[] = [
  { key: "total_data_points", label: "Posts ingested" },
  { key: "unique_streets", label: "Unique streets" },
  { key: "known_locations", label: "Known locations" },
  { key: "unique_businesses", label: "Businesses" },
  { key: "tracked_activities", label: "Activities" },
  { key: "day_patterns", label: "Day patterns" },
];

export function FootprintSummary() {
  const { data, isPending, isError } = useFootprint();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Baseline footprint
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isPending && (
          <div className="grid grid-cols-2 gap-3">
            {STATS.map((s) => (
              <Skeleton key={s.key} className="h-12 w-full" />
            ))}
          </div>
        )}
        {isError && (
          <p className="text-sm text-destructive">Couldn&apos;t load footprint stats.</p>
        )}
        {data && (
          <div className="grid grid-cols-2 gap-3">
            {STATS.map((s) => (
              <div key={s.key}>
                <div className="text-2xl font-semibold">{data.exposure_map[s.key]}</div>
                <div className="text-xs text-muted-foreground">{s.label}</div>
              </div>
            ))}
          </div>
        )}
        {data && data.exposure_map.total_data_points === 0 && (
          <p className="mt-3 text-sm text-muted-foreground">
            Nothing ingested yet — add a post below to build a baseline.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run components/footprint-summary.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/footprint-summary.tsx frontend/components/footprint-summary.test.tsx
git commit -m "Add FootprintSummary component"
```

---

### Task 10: Frontend — IngestionPanel

**Files:**
- Create: `frontend/components/ingestion-panel.tsx`
- Test: `frontend/components/ingestion-panel.test.tsx`

**Interfaces:**
- Consumes: `useIngestManual`, `useIngestExport` (Task 7); `Card`, `Tabs`/`TabsList`/`TabsTrigger`/`TabsContent`, `Textarea`, `Button`, `Alert`/`AlertDescription` from `@/components/ui/*` (Task 2).
- Produces: `<IngestionPanel />`, used by `app/page.tsx` (Task 17).

- [ ] **Step 1: Write the failing tests**

Create `frontend/components/ingestion-panel.test.tsx`:

```tsx
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { IngestionPanel } from "./ingestion-panel";
import { renderWithQueryClient } from "@/lib/test-utils";
import * as api from "@/lib/api";

describe("IngestionPanel", () => {
  it("submits manual entry text and shows the success message", async () => {
    vi.spyOn(api, "ingestManual").mockResolvedValue({
      status: "secured",
      message: "Data Point Secured",
      entry: {} as never,
      detected_entities: { streets: [], places: [], businesses: [], times: [], coordinates: [] },
      exposure_map: {
        total_data_points: 1, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
      final_conclusion: "",
    });

    renderWithQueryClient(<IngestionPanel />);

    fireEvent.change(screen.getByPlaceholderText(/grabbing my usual/i), {
      target: { value: "Coffee on Market Street" },
    });
    fireEvent.click(screen.getByRole("button", { name: /add to baseline/i }));

    await waitFor(() => expect(screen.getByText("Data Point Secured")).toBeInTheDocument());
    expect(api.ingestManual).toHaveBeenCalled();
  });

  it("switches to the export tab and submits a zip file", async () => {
    vi.spyOn(api, "ingestExport").mockResolvedValue({
      status: "synced",
      posts_available: 10,
      posts_ingested: 10,
      posts_skipped: 0,
      exposure_map: {
        total_data_points: 10, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
    });

    renderWithQueryClient(<IngestionPanel />);

    fireEvent.click(screen.getByRole("tab", { name: /import export/i }));
    const file = new File(["zip-bytes"], "export.zip", { type: "application/zip" });
    const fileInput = screen.getByLabelText(/export file/i) as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: /import export/i }));

    await waitFor(() =>
      expect(screen.getByText(/10 posts ingested, 0 skipped/i)).toBeInTheDocument(),
    );
  });

  it("disables the manual submit button when the text field is empty", () => {
    renderWithQueryClient(<IngestionPanel />);

    expect(screen.getByRole("button", { name: /add to baseline/i })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run components/ingestion-panel.test.tsx`
Expected: FAIL — component doesn't exist yet.

- [ ] **Step 3: Implement the component**

Create `frontend/components/ingestion-panel.tsx`:

```tsx
"use client";

import { useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useIngestExport, useIngestManual } from "@/lib/hooks/use-ingest";

export function IngestionPanel() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Build your baseline
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="manual">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="manual">Manual entry</TabsTrigger>
            <TabsTrigger value="export">Import export</TabsTrigger>
          </TabsList>
          <TabsContent value="manual">
            <ManualEntryForm />
          </TabsContent>
          <TabsContent value="export">
            <ExportImportForm />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function ManualEntryForm() {
  const [text, setText] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const mutation = useIngestManual();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const formData = new FormData();
    formData.set("text", text);
    if (image) formData.set("image", image);
    mutation.mutate(formData, {
      onSuccess: () => {
        setText("");
        setImage(null);
      },
    });
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
      <Textarea
        placeholder="Grabbing my usual morning coffee down on Market Street"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
      />
      <label className="text-sm text-muted-foreground">
        Optional image
        <input
          type="file"
          accept="image/*"
          aria-label="manual entry image"
          onChange={(e) => setImage(e.target.files?.[0] ?? null)}
          className="mt-1 block text-sm"
        />
      </label>
      <Button type="submit" disabled={mutation.isPending || !text.trim()}>
        {mutation.isPending ? "Securing…" : "Add to baseline"}
      </Button>
      {mutation.isSuccess && mutation.data.status === "secured" && (
        <Alert>
          <AlertDescription>{mutation.data.message}</AlertDescription>
        </Alert>
      )}
      {mutation.isError && (
        <Alert variant="destructive">
          <AlertDescription>{(mutation.error as Error).message}</AlertDescription>
        </Alert>
      )}
    </form>
  );
}

function ExportImportForm() {
  const [file, setFile] = useState<File | null>(null);
  const mutation = useIngestExport();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    const formData = new FormData();
    formData.set("file", file);
    mutation.mutate(formData, { onSuccess: () => setFile(null) });
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
      <label className="text-sm text-muted-foreground">
        Instagram data export (.zip)
        <input
          type="file"
          accept=".zip"
          aria-label="export file"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="mt-1 block text-sm"
        />
      </label>
      <Button type="submit" disabled={mutation.isPending || !file}>
        {mutation.isPending ? "Importing…" : "Import export"}
      </Button>
      {mutation.isSuccess && mutation.data.status === "synced" && (
        <Alert>
          <AlertDescription>
            {mutation.data.posts_ingested} posts ingested, {mutation.data.posts_skipped} skipped.
          </AlertDescription>
        </Alert>
      )}
      {mutation.isSuccess && mutation.data.status === "error" && (
        <Alert variant="destructive">
          <AlertDescription>{mutation.data.message}</AlertDescription>
        </Alert>
      )}
      {mutation.isError && (
        <Alert variant="destructive">
          <AlertDescription>{(mutation.error as Error).message}</AlertDescription>
        </Alert>
      )}
    </form>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run components/ingestion-panel.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/ingestion-panel.tsx frontend/components/ingestion-panel.test.tsx
git commit -m "Add IngestionPanel (manual entry + export import) component"
```

---

### Task 11: Frontend — AnalysisForm

**Files:**
- Create: `frontend/components/analysis-form.tsx`
- Test: `frontend/components/analysis-form.test.tsx`

**Interfaces:**
- Consumes: `useAnalyze` (Task 7); `AnalyzeThreatResult` type (Task 3).
- Produces: `<AnalysisForm onResult={(result: AnalyzeThreatResult) => void} />`, used by `app/page.tsx` (Task 17).

- [ ] **Step 1: Write the failing tests**

Create `frontend/components/analysis-form.test.tsx`:

```tsx
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AnalysisForm } from "./analysis-form";
import { renderWithQueryClient } from "@/lib/test-utils";
import * as api from "@/lib/api";

describe("AnalysisForm", () => {
  it("calls onResult with the analysis result on success", async () => {
    const result = {
      status: "analyzed" as const,
      detected_entities: { streets: [], places: [], businesses: [], times: [], coordinates: [] },
      category_similarity: {},
      breach_probability: 55,
      vulnerability_map: [],
      static_landmarks: [],
      entity_triplets: [],
      final_conclusion: "Baseline established.",
      signals: {
        draft_text_length: 5, ocr_text: null, ocr_high_value: null,
        exif_metadata: null, time_context: null, merged_length: 5,
      },
      web: { nodes: [], edges: [] },
      exposure_map: {
        total_data_points: 1, unique_streets: 0, known_locations: 0,
        unique_businesses: 0, tracked_activities: 0, day_patterns: 0,
      },
    };
    vi.spyOn(api, "analyzeThreat").mockResolvedValue(result);
    const onResult = vi.fn();

    renderWithQueryClient(<AnalysisForm onResult={onResult} />);

    fireEvent.change(screen.getByPlaceholderText(/draft the post/i), {
      target: { value: "Heading to the gym" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^analyze$/i }));

    await waitFor(() => expect(onResult).toHaveBeenCalledWith(result));
  });

  it("disables the analyze button while text is empty", () => {
    renderWithQueryClient(<AnalysisForm onResult={vi.fn()} />);

    expect(screen.getByRole("button", { name: /^analyze$/i })).toBeDisabled();
  });

  it("shows an error message when analysis fails", async () => {
    vi.spyOn(api, "analyzeThreat").mockRejectedValue(new Error("server exploded"));

    renderWithQueryClient(<AnalysisForm onResult={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText(/draft the post/i), {
      target: { value: "test" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^analyze$/i }));

    await waitFor(() => expect(screen.getByText("server exploded")).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run components/analysis-form.test.tsx`
Expected: FAIL — component doesn't exist yet.

- [ ] **Step 3: Implement the component**

Create `frontend/components/analysis-form.tsx`:

```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useAnalyze } from "@/lib/hooks/use-analyze";
import type { AnalyzeThreatResult } from "@/lib/api-types";

export function AnalysisForm({
  onResult,
}: {
  onResult: (result: AnalyzeThreatResult) => void;
}) {
  const [text, setText] = useState("");
  const [image, setImage] = useState<File | null>(null);
  const mutation = useAnalyze();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const formData = new FormData();
    formData.set("text", text);
    if (image) formData.set("image", image);
    mutation.mutate(formData, { onSuccess: (result) => onResult(result) });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Analyze a draft post
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <Textarea
            placeholder="Draft the post you're thinking about publishing…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={3}
          />
          <label className="text-sm text-muted-foreground">
            Optional image
            <input
              type="file"
              accept="image/*"
              aria-label="analysis image"
              onChange={(e) => setImage(e.target.files?.[0] ?? null)}
              className="mt-1 block text-sm"
            />
          </label>
          <Button type="submit" disabled={mutation.isPending || !text.trim()}>
            {mutation.isPending ? "Analyzing…" : "Analyze"}
          </Button>
          {mutation.isError && (
            <p className="text-sm text-destructive">{(mutation.error as Error).message}</p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run components/analysis-form.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/analysis-form.tsx frontend/components/analysis-form.test.tsx
git commit -m "Add AnalysisForm component"
```

---

### Task 12: Frontend — BreachGauge

**Files:**
- Create: `frontend/components/breach-gauge.tsx`
- Test: `frontend/components/breach-gauge.test.tsx`

**Interfaces:**
- Consumes: `cn` from `@/lib/utils` (Task 2).
- Produces: `<BreachGauge score={number} />` and exported `bandFor(score: number)` for direct unit testing. Used by `app/page.tsx` (Task 17).

- [ ] **Step 1: Write the failing tests**

Create `frontend/components/breach-gauge.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BreachGauge, bandFor } from "./breach-gauge";

describe("bandFor", () => {
  it("labels 70+ as Critical", () => {
    expect(bandFor(85).label).toBe("Critical");
  });
  it("labels 40-69 as Moderate", () => {
    expect(bandFor(50).label).toBe("Moderate");
  });
  it("labels 15-39 as Low", () => {
    expect(bandFor(20).label).toBe("Low");
  });
  it("labels under 15 as Minimal", () => {
    expect(bandFor(5).label).toBe("Minimal");
  });
});

describe("BreachGauge", () => {
  it("renders the rounded score and band label", () => {
    render(<BreachGauge score={72.6} />);

    expect(screen.getByText("73%")).toBeInTheDocument();
    expect(screen.getByText("Critical")).toBeInTheDocument();
  });

  it("clamps out-of-range scores into 0-100", () => {
    render(<BreachGauge score={150} />);

    expect(screen.getByText("100%")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run components/breach-gauge.test.tsx`
Expected: FAIL — component doesn't exist yet.

- [ ] **Step 3: Implement the component**

Create `frontend/components/breach-gauge.tsx`:

```tsx
import { cn } from "@/lib/utils";

const RADIUS = 54;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function bandFor(score: number): { label: string; className: string } {
  if (score >= 70) return { label: "Critical", className: "text-severity-critical stroke-severity-critical" };
  if (score >= 40) return { label: "Moderate", className: "text-severity-high stroke-severity-high" };
  if (score >= 15) return { label: "Low", className: "text-severity-medium stroke-severity-medium" };
  return { label: "Minimal", className: "text-severity-low stroke-severity-low" };
}

export function BreachGauge({ score }: { score: number }) {
  const clamped = Math.max(0, Math.min(100, score));
  const offset = CIRCUMFERENCE - (clamped / 100) * CIRCUMFERENCE;
  const band = bandFor(clamped);

  return (
    <div
      className="relative flex h-[140px] w-[140px] items-center justify-center"
      role="img"
      aria-label={`Breach probability ${Math.round(clamped)}%, ${band.label}`}
    >
      <svg width={140} height={140} viewBox="0 0 140 140" className="-rotate-90">
        <circle cx={70} cy={70} r={RADIUS} strokeWidth={10} className="stroke-muted" fill="none" />
        <circle
          cx={70}
          cy={70}
          r={RADIUS}
          strokeWidth={10}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          className={cn("transition-[stroke-dashoffset] duration-500", band.className)}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-bold">{Math.round(clamped)}%</span>
        <span className={cn("text-xs font-medium uppercase tracking-wide", band.className)}>
          {band.label}
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run components/breach-gauge.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/breach-gauge.tsx frontend/components/breach-gauge.test.tsx
git commit -m "Add BreachGauge component"
```

---

### Task 13: Frontend — FindingsList

**Files:**
- Create: `frontend/components/findings-list.tsx`
- Test: `frontend/components/findings-list.test.tsx`

**Interfaces:**
- Consumes: `VulnerabilityFinding` type (Task 3); `Badge`, `Card`/`CardHeader`/`CardTitle`/`CardContent` from `@/components/ui/*` (Task 2).
- Produces: `<FindingsList findings={VulnerabilityFinding[]} />` and exported `groupBySeverity(findings)`. Used by `app/page.tsx` (Task 17).

- [ ] **Step 1: Write the failing tests**

Create `frontend/components/findings-list.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FindingsList, groupBySeverity } from "./findings-list";
import type { VulnerabilityFinding } from "@/lib/api-types";

const FINDINGS: VulnerabilityFinding[] = [
  { category: "Routine Leak", severity: "high", finding: "You post from home every morning", evidence_count: 3 },
  { category: "Identity Leak", severity: "critical", finding: "Street matches your home cluster", evidence_count: 1 },
  { category: "Metadata Leak", severity: "medium", finding: "Image has GPS coordinates", evidence_count: 1 },
];

describe("groupBySeverity", () => {
  it("buckets findings by severity", () => {
    const groups = groupBySeverity(FINDINGS);
    expect(groups.critical).toHaveLength(1);
    expect(groups.high).toHaveLength(1);
    expect(groups.medium).toHaveLength(1);
    expect(groups.low).toHaveLength(0);
  });
});

describe("FindingsList", () => {
  it("renders each finding grouped under its severity badge", () => {
    render(<FindingsList findings={FINDINGS} />);

    expect(screen.getByText("Critical")).toBeInTheDocument();
    expect(screen.getByText("Street matches your home cluster")).toBeInTheDocument();
    expect(screen.getByText("You post from home every morning")).toBeInTheDocument();
  });

  it("shows a no-vulnerabilities message when the list is empty", () => {
    render(<FindingsList findings={[]} />);

    expect(screen.getByText(/no vulnerabilities detected/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run components/findings-list.test.tsx`
Expected: FAIL — component doesn't exist yet.

- [ ] **Step 3: Implement the component**

Create `frontend/components/findings-list.tsx`:

```tsx
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { VulnerabilityFinding } from "@/lib/api-types";

const SEVERITY_ORDER: VulnerabilityFinding["severity"][] = ["critical", "high", "medium", "low"];

const SEVERITY_LABEL: Record<VulnerabilityFinding["severity"], string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

const SEVERITY_BADGE_CLASS: Record<VulnerabilityFinding["severity"], string> = {
  critical: "bg-severity-critical/15 text-severity-critical border-severity-critical/30",
  high: "bg-severity-high/15 text-severity-high border-severity-high/30",
  medium: "bg-severity-medium/15 text-severity-medium border-severity-medium/30",
  low: "bg-severity-low/15 text-severity-low border-severity-low/30",
};

export function groupBySeverity(
  findings: VulnerabilityFinding[],
): Record<VulnerabilityFinding["severity"], VulnerabilityFinding[]> {
  const groups: Record<VulnerabilityFinding["severity"], VulnerabilityFinding[]> = {
    critical: [],
    high: [],
    medium: [],
    low: [],
  };
  for (const finding of findings) {
    groups[finding.severity].push(finding);
  }
  return groups;
}

export function FindingsList({ findings }: { findings: VulnerabilityFinding[] }) {
  if (findings.length === 0) {
    return <p className="text-sm text-muted-foreground">No vulnerabilities detected in this draft.</p>;
  }

  const groups = groupBySeverity(findings);

  return (
    <div className="flex flex-col gap-4">
      {SEVERITY_ORDER.filter((sev) => groups[sev].length > 0).map((sev) => (
        <div key={sev}>
          <div className="mb-2 flex items-center gap-2">
            <Badge variant="outline" className={SEVERITY_BADGE_CLASS[sev]}>
              {SEVERITY_LABEL[sev]}
            </Badge>
            <span className="text-xs text-muted-foreground">{groups[sev].length} finding(s)</span>
          </div>
          <div className="flex flex-col gap-2">
            {groups[sev].map((finding, i) => (
              <Card key={`${sev}-${i}`}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">{finding.category}</CardTitle>
                </CardHeader>
                <CardContent className="pt-0 text-sm text-muted-foreground">
                  {finding.finding}
                  <span className="ml-2 text-xs">({finding.evidence_count} evidence)</span>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run components/findings-list.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/findings-list.tsx frontend/components/findings-list.test.tsx
git commit -m "Add FindingsList component"
```

---

### Task 14: Frontend — ConclusionNarrative and EmptyState

**Files:**
- Create: `frontend/components/conclusion-narrative.tsx`
- Create: `frontend/components/empty-state.tsx`

**Interfaces:**
- Produces: `<ConclusionNarrative text={string} />`, `<EmptyState />`. Used by `app/page.tsx` (Task 17).
- No tests: both are pure presentational components with no conditional logic beyond splitting on a delimiter — consistent with the spec's stated test philosophy (cover branching logic, not markup).

- [ ] **Step 1: Implement ConclusionNarrative**

Create `frontend/components/conclusion-narrative.tsx`:

```tsx
export function ConclusionNarrative({ text }: { text: string }) {
  const paragraphs = text.split("\n\n").filter(Boolean);
  return (
    <div className="flex flex-col gap-3 text-sm leading-relaxed text-foreground">
      {paragraphs.map((p, i) => (
        <p key={i}>{p}</p>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Implement EmptyState**

Create `frontend/components/empty-state.tsx`:

```tsx
import { ShieldQuestion } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border p-12 text-center">
      <ShieldQuestion className="h-8 w-8 text-muted-foreground" />
      <div>
        <p className="font-medium">No analysis yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Ingest a few baseline posts on the left, then draft a post below and analyze it to see what it reveals.
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify compilation**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/conclusion-narrative.tsx frontend/components/empty-state.tsx
git commit -m "Add ConclusionNarrative and EmptyState components"
```

---

### Task 15: Frontend — ScoreHistoryChart

**Files:**
- Create: `frontend/components/score-history-chart.tsx`
- Test: `frontend/components/score-history-chart.test.tsx`

**Interfaces:**
- Consumes: `useScoreHistory` (Task 6), `recharts`.
- Produces: `<ScoreHistoryChart />` and exported `formatHistoryForChart(history)`. Used by `app/page.tsx` (Task 17).

- [ ] **Step 1: Write the failing tests**

Create `frontend/components/score-history-chart.test.tsx`:

```tsx
import { screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ScoreHistoryChart, formatHistoryForChart } from "./score-history-chart";
import { renderWithQueryClient } from "@/lib/test-utils";
import * as api from "@/lib/api";

describe("formatHistoryForChart", () => {
  it("assigns a 1-based index to each entry, preserving order", () => {
    const formatted = formatHistoryForChart([
      { timestamp: "2026-01-01T00:00:00Z", breach_probability: 10, severity_counts: { critical: 0, high: 0, medium: 0, low: 0 }, entity_counts: {} },
      { timestamp: "2026-01-02T00:00:00Z", breach_probability: 30, severity_counts: { critical: 0, high: 0, medium: 0, low: 0 }, entity_counts: {} },
    ]);

    expect(formatted.map((f) => f.index)).toEqual([1, 2]);
    expect(formatted.map((f) => f.breach_probability)).toEqual([10, 30]);
  });
});

describe("ScoreHistoryChart", () => {
  it("shows a no-analyses message when history is empty", async () => {
    vi.spyOn(api, "fetchScoreHistory").mockResolvedValue({ history: [] });

    renderWithQueryClient(<ScoreHistoryChart />);

    await waitFor(() => expect(screen.getByText(/no analyses yet/i)).toBeInTheDocument());
  });

  it("shows an error message if the query fails", async () => {
    vi.spyOn(api, "fetchScoreHistory").mockRejectedValue(new Error("down"));

    renderWithQueryClient(<ScoreHistoryChart />);

    await waitFor(() =>
      expect(screen.getByText(/couldn't load score history/i)).toBeInTheDocument(),
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run components/score-history-chart.test.tsx`
Expected: FAIL — component doesn't exist yet.

- [ ] **Step 3: Implement the component**

Create `frontend/components/score-history-chart.tsx`:

```tsx
"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useScoreHistory } from "@/lib/hooks/use-score-history";
import type { ScoreHistoryEntryDict } from "@/lib/api-types";

export function formatHistoryForChart(history: ScoreHistoryEntryDict[]) {
  return history.map((entry, i) => ({
    index: i + 1,
    timestamp: new Date(entry.timestamp).toLocaleString(),
    breach_probability: entry.breach_probability,
  }));
}

export function ScoreHistoryChart() {
  const { data, isPending, isError } = useScoreHistory();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Breach probability over time
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isPending && <Skeleton className="h-40 w-full" />}
        {isError && <p className="text-sm text-destructive">Couldn&apos;t load score history.</p>}
        {data && data.history.length === 0 && (
          <p className="text-sm text-muted-foreground">No analyses yet.</p>
        )}
        {data && data.history.length > 0 && (
          <ResponsiveContainer width="100%" height={160}>
            <LineChart data={formatHistoryForChart(data.history)}>
              <XAxis dataKey="index" tick={false} />
              <YAxis domain={[0, 100]} width={30} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(value: number) => [`${value}%`, "Breach probability"]}
                labelFormatter={(_, payload) => payload?.[0]?.payload?.timestamp ?? ""}
              />
              <Line type="monotone" dataKey="breach_probability" stroke="currentColor" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run components/score-history-chart.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/score-history-chart.tsx frontend/components/score-history-chart.test.tsx
git commit -m "Add ScoreHistoryChart component"
```

---

### Task 16: Frontend — EntityGraph

**Files:**
- Create: `frontend/components/entity-graph.tsx`
- Test: `frontend/components/entity-graph.test.tsx`

**Interfaces:**
- Consumes: `GraphNode`, `GraphEdge` types (Task 3); `react-force-graph-2d` (dynamically imported, `ssr: false`).
- Produces: `<EntityGraph nodes={GraphNode[]} edges={GraphEdge[]} />` and exported `toForceGraphData(nodes, edges)`. Used by `app/page.tsx` (Task 17).

- [ ] **Step 1: Write the failing tests**

Create `frontend/components/entity-graph.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EntityGraph, toForceGraphData } from "./entity-graph";
import type { GraphEdge, GraphNode } from "@/lib/api-types";

vi.mock("react-force-graph-2d", () => ({
  default: () => <div data-testid="force-graph-stub" />,
}));

const NODES: GraphNode[] = [
  { id: "new_post", label: "Your Draft Post", type: "post", color: "#f59e0b" },
  { id: "fp_1", label: "Coffee, Market Street", type: "footprint", color: "#ef4444" },
];
const EDGES: GraphEdge[] = [
  { source: "new_post", target: "fp_1", type: "identity_link", weight: 0.4, label: "both mention Market Street" },
];

describe("toForceGraphData", () => {
  it("maps nodes/edges into the react-force-graph-2d graphData shape", () => {
    const data = toForceGraphData(NODES, EDGES);
    expect(data.nodes).toEqual([
      { id: "new_post", label: "Your Draft Post", color: "#f59e0b" },
      { id: "fp_1", label: "Coffee, Market Street", color: "#ef4444" },
    ]);
    expect(data.links).toEqual([
      { source: "new_post", target: "fp_1", label: "both mention Market Street", value: 0.4 },
    ]);
  });
});

describe("EntityGraph", () => {
  it("renders the graph card when there are nodes", () => {
    render(<EntityGraph nodes={NODES} edges={EDGES} />);
    expect(screen.getByText(/entity relationship graph/i)).toBeInTheDocument();
  });

  it("renders nothing when there are no nodes", () => {
    const { container } = render(<EntityGraph nodes={[]} edges={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run components/entity-graph.test.tsx`
Expected: FAIL — component doesn't exist yet.

- [ ] **Step 3: Implement the component**

Create `frontend/components/entity-graph.tsx`:

```tsx
"use client";

import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GraphEdge, GraphNode } from "@/lib/api-types";

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

export function toForceGraphData(nodes: GraphNode[], edges: GraphEdge[]) {
  return {
    nodes: nodes.map((n) => ({ id: n.id, label: n.label, color: n.color })),
    links: edges.map((e) => ({ source: e.source, target: e.target, label: e.label, value: e.weight })),
  };
}

export function EntityGraph({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  if (nodes.length === 0) {
    return null;
  }

  const data = toForceGraphData(nodes, edges);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Entity relationship graph
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[320px] w-full overflow-hidden rounded-md border border-border">
          <ForceGraph2D
            graphData={data}
            nodeLabel="label"
            nodeColor={(n: { color?: string }) => n.color ?? "#888"}
            linkLabel="label"
            width={480}
            height={320}
            backgroundColor="transparent"
          />
        </div>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run components/entity-graph.test.tsx`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/entity-graph.tsx frontend/components/entity-graph.test.tsx
git commit -m "Add EntityGraph component"
```

---

### Task 17: Frontend — page composition and deletion of old components

**Files:**
- Modify: `frontend/app/page.tsx`
- Delete: `frontend/components/HexDashboard.tsx`, `frontend/components/MatrixRain.tsx`, `frontend/components/TypingEffect.tsx`, `frontend/components/DigitalShadow.tsx`, `frontend/components/VisualizationWrapper.tsx`, `frontend/components/SimulateForm.tsx`, `frontend/components/AuditResult.tsx`, `frontend/components/RiskGauge.tsx`, `frontend/components/ScoreTracker.tsx`, `frontend/components/StalkerWeb.tsx`

**Interfaces:**
- Consumes: every component from Tasks 9-16.

- [ ] **Step 1: Delete the superseded components**

```bash
cd frontend
rm components/HexDashboard.tsx components/MatrixRain.tsx components/TypingEffect.tsx components/DigitalShadow.tsx components/VisualizationWrapper.tsx components/SimulateForm.tsx components/AuditResult.tsx components/RiskGauge.tsx components/ScoreTracker.tsx components/StalkerWeb.tsx
```

- [ ] **Step 2: Replace app/page.tsx**

Replace the full contents of `frontend/app/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { AnalysisForm } from "@/components/analysis-form";
import { BreachGauge } from "@/components/breach-gauge";
import { ConclusionNarrative } from "@/components/conclusion-narrative";
import { EmptyState } from "@/components/empty-state";
import { EntityGraph } from "@/components/entity-graph";
import { FindingsList } from "@/components/findings-list";
import { FootprintSummary } from "@/components/footprint-summary";
import { IngestionPanel } from "@/components/ingestion-panel";
import { ScoreHistoryChart } from "@/components/score-history-chart";
import type { AnalyzeThreatResult } from "@/lib/api-types";

export default function Home() {
  const [result, setResult] = useState<AnalyzeThreatResult | null>(null);

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 p-6">
      <header className="flex items-baseline justify-between border-b border-border pb-4">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Aegis</h1>
          <p className="text-xs text-muted-foreground">Personal Privacy Intelligence Engine</p>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
        <div className="flex flex-col gap-6">
          <FootprintSummary />
          <IngestionPanel />
          <ScoreHistoryChart />
        </div>

        <div className="flex flex-col gap-6">
          <AnalysisForm onResult={setResult} />

          {!result && <EmptyState />}

          {result && result.status !== "analyzed" && (
            <p className="text-sm text-muted-foreground">{result.message}</p>
          )}

          {result && result.status === "analyzed" && (
            <>
              <div className="flex items-center gap-6">
                <BreachGauge score={result.breach_probability} />
                <ConclusionNarrative text={result.final_conclusion} />
              </div>
              <FindingsList findings={result.vulnerability_map} />
              <EntityGraph nodes={result.web.nodes} edges={result.web.edges} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify the app builds**

Run: `cd frontend && npm run build`
Expected: build succeeds with no type or import errors (this will catch any dangling reference to a deleted component).

- [ ] **Step 4: Run the full frontend test suite**

Run: `cd frontend && npm test`
Expected: all tests from Tasks 4, 6, 7, 9-13, 15-16 pass.

- [ ] **Step 5: Commit**

```bash
git add -A frontend/
git commit -m "Compose the new app page, remove superseded hackathon-era components"
```

---

### Task 18: Deployment configuration

**Files:**
- Create: `frontend/.env.example`
- Modify: `README.md`

**Interfaces:**
- None — this is configuration/documentation only.

- [ ] **Step 1: Create the frontend env example**

Create `frontend/.env.example`:

```
# URL of the deployed backend (Render/Railway). Defaults to
# http://localhost:8000 in local dev if unset.
NEXT_PUBLIC_API_BASE_URL=
```

- [ ] **Step 2: Update the README's Getting Started / deployment sections**

In `README.md`, replace the existing `## Getting Started` section's env-var block and add a new `## Deployment` section after it:

```markdown
Create `frontend/.env.local` for local dev (optional — defaults to `http://localhost:8000`):
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Deployment

**Frontend (Vercel):** import the repo, set the root directory to `frontend/`, and set the `NEXT_PUBLIC_API_BASE_URL` environment variable to the deployed backend's URL.

**Backend (Render or Railway):** deploy `backend/` (Dockerfile included) with a managed Postgres add-on. Required environment variables:
```
DATABASE_URL=<provided by the Postgres add-on>
CORS_ORIGINS=["https://<your-vercel-app>.vercel.app"]
SESSION_COOKIE_NAME=aegis_session_id
TESSERACT_CMD=            # leave unset to auto-detect on the host image
NER_MODEL_DIR=            # optional, path to a fine-tuned NER model
VISION_MODEL_PATH=        # optional, path to a fine-tuned vision model
```
The session cookie is set with `samesite="none", secure=True` specifically so it survives the cross-origin Vercel-to-Render/Railway hop — don't relax this back to `"lax"` unless the frontend and backend end up sharing a domain.
```

- [ ] **Step 3: Remove the now-stale "Known limitation" line about HexDashboard.tsx**

In `README.md`, delete the line:
```
**Known limitation, not yet addressed:** the frontend's `HexDashboard.tsx` component is still imported and rendered in `AuditResult.tsx`, hardcoded to the original author's Hex.tech embed URL. It's now orphaned — the backend no longer sends it data — and needs to be removed or replaced with an in-house visualization built on the data the API already returns. Everything else in the table above is done.
```
Replace it with:
```
This frontend rebuild removed the orphaned `HexDashboard.tsx` entirely and replaced it with an in-house UI (see `docs/superpowers/specs/2026-08-21-frontend-rebuild-design.md`). Every item in the table above is now done.
```

- [ ] **Step 4: Update the Project Structure section's frontend tree**

Replace the `frontend/` block in `README.md`'s `## Project Structure` section with:

```markdown
└── frontend/
    ├── app/                     # Next.js app router (single page)
    ├── components/
    │   ├── ui/                   # shadcn/ui primitives
    │   ├── footprint-summary.tsx
    │   ├── ingestion-panel.tsx
    │   ├── analysis-form.tsx
    │   ├── breach-gauge.tsx
    │   ├── findings-list.tsx
    │   ├── conclusion-narrative.tsx
    │   ├── score-history-chart.tsx
    │   ├── entity-graph.tsx
    │   └── empty-state.tsx
    └── lib/
        ├── api.ts                 # typed fetch client
        ├── api-types.ts           # backend response types
        └── hooks/                 # TanStack Query hooks
```

- [ ] **Step 5: Commit**

```bash
git add frontend/.env.example README.md
git commit -m "Document deployment (Vercel + Render/Railway) and update README for the frontend rebuild"
```

---

## Self-review notes

- **Spec coverage**: architecture (Task 8, 17), all listed components (Tasks 9-16), data flow/invalidation rules (Tasks 6-7), error handling for both HTTP and in-band logical errors (Task 4, exercised in Tasks 9-11), free-tier cold-start UX is intentionally left as a follow-up polish item, not a blocking task — noted here rather than silently dropped, since the spec called it out as "worth a small UX touch," not a hard requirement. Testing scope (Tasks 4, 6, 7, 9-13, 15-16) covers every component with real logic; Task 14 documents why two components are intentionally untested. Deployment (Task 18) covers both the cookie fix (Task 1) and CORS/env var configuration.
- **Type consistency**: `AnalyzeThreatResult`, `IngestManualResult`, `IngestExportResult` discriminated unions defined once in Task 3 and referenced identically (same field names, same status literals) in every later task — checked against the exact backend response shapes read from `analysis.py`, `vulnerability.py`, `graph.py`, `repository.py`, and `orm.py` during design.
- **Known gap deliberately out of scope**: the free-tier cold-start loading-message UX touch mentioned in the spec's error-handling section is not a separate task — it's a small enhancement to `AnalysisForm`/`IngestionPanel`'s loading state that can be added after this plan lands, once the actual Render/Railway cold-start behavior can be observed live.
