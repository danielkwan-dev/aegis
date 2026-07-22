# Aegis | Personal Privacy Intelligence Engine

Aegis detects **Identity Links** — cross-post patterns of location, time, and activity that let a threat actor reconstruct someone's daily routine from public posts alone. Built solo for YaleHack 2026, then rebuilt from the ground up into a tested, fine-tuned-ML system.

**Devpost:** https://devpost.com/software/aegis-68rmo0
**Hackathon Demo Video:** https://youtu.be/Nf_50lff9Rc *(shows the original hackathon build — live scraping, a Hex.tech dashboard, JSONBlob persistence. See [What changed since the hackathon](#what-changed-since-the-hackathon) for the rebuild.)*
**Author:** Daniel Kwan ([@danielkwan-dev](https://github.com/danielkwan-dev))

---

## Screenshots

Live from the rebuilt frontend, running against the real backend and fine-tuned NER model:

![Analysis result — breach gauge, severity-grouped findings, and the entity relationship graph](docs/screenshots/analysis-result.png)

![Empty state before any data has been ingested](docs/screenshots/empty-state.png)

---

## The Problem

Standard security tooling covers network intrusion, malware, and credential theft — nothing addresses the slow-burn threat of behavioral pattern exposure through social media. A stalker, investigator, or state actor doesn't need to compromise a system. They just need to read a feed.

| Adversary | What Aegis Detects |
|---|---|
| Stalker / Harasser | Home neighbourhood, daily schedule, recurring locations |
| Corporate Investigator | Workplace, travel patterns, relationship network |
| State-Level Actor | Full behavioral profile, vulnerability windows, predictive location |

**Attack vectors modeled:** location triangulation from cross-post geography, temporal pattern analysis from posting-time consistency, OCR side-channel leaks (street signs, storefronts in photo backgrounds), EXIF geolocation, and routine prediction from historical anchors.

---

## Machine Learning Pipeline

1. **Entity extraction** — fine-tuned **DistilBERT** token classification (streets, landmarks, businesses, times, activities), trained via weak supervision + hand-corrected gold labels. Falls back to the regex/keyword extractor when no trained model is configured, so the app is never non-functional.
2. **Vision cascade** — fine-tuned **YOLOv8n** signage detector driving a **detect → crop → preprocess → OCR → NER** pipeline: find signage, crop and contrast-enhance each region, OCR each crop individually, then extract entities.
3. **EXIF + OCR signal fusion** — Pillow for GPS/timestamp metadata, Tesseract for any text baked into an image.
4. **Geocoding** — free-text locations resolved via Nominatim (OpenStreetMap), Postgres-cached to respect rate limits.
5. **Geospatial risk clustering** — DBSCAN + Haversine distance splits GPS coordinates into two distinct signals: dense repeat-visit clusters ("**Routine Exposure**," predictable/high-risk) vs. one-off outliers ("**Anomalous Disclosure**," sensitive but not a pattern) — deliberately not conflated into one score.
6. **TF-IDF similarity scoring** — three vectorizers (locations, timestamps, activities), cosine-scored against baseline history for a weighted breach-probability score (0–100%).
7. **Entity triplet detection** — co-occurrence analysis finds recurring (time, location, activity) triplets; consistent-timing ones become static-landmark findings.
8. **K-Means routine clustering** — baseline posts clustered to surface distinct behavioral routines and their predictability.
9. **Vulnerability map + conclusion narrative** — every finding gets a severity, evidence count, and risk-reduction-if-removed, synthesized into a readable narrative.

### Trained model results

| Model | Metric | Result | Deployed size |
|---|---|---|---|
| NER (DistilBERT, fine-tuned) | Entity F1 | 0.851 | 265.6MB |
| NER (int8 quantized, ONNX) | Entity F1 | 0.832 | **66.8MB** (4.0x smaller, ~34% faster) |
| Vision (YOLOv8n, fine-tuned) | mAP50 / mAP50-95 | 0.567 / 0.333 | 12.3MB |
| Vision (int8 quantized, ONNX) | — | — | **3.4MB** (3.6x smaller) |

NER per-category F1: STREET 0.883, TIME 0.923, BUSINESS 0.900, ACTIVITY 0.859, LANDMARK 0.273 (weak — only 26 gold examples, a known limitation). Both trained on a free Colab T4 GPU, exported to ONNX + quantized. If no trained weights are configured, the app falls back to the regex baseline / whole-image OCR automatically — fully functional either way, just less accurate. Full training pipeline (weak-label bootstrapping, hand-correction, Colab steps) in [`backend/ml_training/COLAB.md`](backend/ml_training/COLAB.md).

---

## Architecture

- **Backend** — Python/FastAPI, layered (`api/` routers → `services/` business logic → `db/`/`models/` persistence), PostgreSQL + SQLAlchemy, Docker Compose. Per-session state (not a global store). Serves ML inference via `onnxruntime`/`tokenizers` only — no `torch`/`transformers` at request time; those stay in `ml_training/`'s separate venv (`transformers`, `ultralytics`, `optimum`), which trains on Colab and publishes to Hugging Face Hub.
- **Frontend** — Next.js 14, TypeScript, TailwindCSS, `shadcn/ui`, TanStack Query, Recharts, `react-force-graph-2d`, Framer Motion.
- **Testing** — 63 backend (pytest) + 38 frontend (Vitest/RTL) unit tests, all dependency-injected — no live models, weights, or network needed to run them.
- **Ingestion** — no live scraping (the original build's Instaloader use violated Instagram's ToS). Now: official Instagram data export (`.zip`, bulk) or manual single-post entry, both via `/api/ingest/*`.

---

## What changed since the hackathon

Aegis won YaleHack 2026, but shipped with real hackathon debt — hardcoded lookups, sponsor-tool dependencies (Hex.tech, JSONBlob) standing in for a database, a dead duplicate frontend scaffold, and ToS-violating scraping. Rebuilt end to end:

| Area | Hackathon build | Current build |
|---|---|---|
| Data ingestion | Live Instagram scraping (Instaloader) | Official data export + manual entry (ToS-compliant) |
| Entity extraction | Regex + hardcoded lexicon only | Fine-tuned DistilBERT NER, regex as fallback |
| Image signal extraction | Whole-image OCR only | YOLOv8-detected crops → OCR → NER cascade |
| Geospatial clustering | Fixed-degree coordinate bucketing | DBSCAN + Haversine, dual risk signals |
| Location resolution | Hardcoded 10-entry coordinate dict | Nominatim geocoding, Postgres-cached |
| Persistence | In-memory store + JSONBlob | PostgreSQL |
| Analytics dashboard | Hex.tech notebook embed (backend round-trip) | In-house UI, no external call in the critical path |
| Testing | None | 63 backend + 38 frontend unit tests |

---

## Getting Started

**Prerequisites:** Docker, Node.js 18+, Python 3.11+, Tesseract OCR installed locally.

```bash
# Backend (Postgres + API)
cd backend
docker compose up -d db
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install && npm run dev
```

`backend/.env` (see `backend/.env.example` for the authoritative list) — `NER_MODEL_DIR`/`VISION_MODEL_PATH` are optional; leave unset and the app runs on the regex extractor / whole-image OCR instead:
```
DATABASE_URL=postgresql+psycopg2://aegis:aegis@localhost:5432/aegis
TESSERACT_CMD=            # leave unset to auto-detect
NER_MODEL_DIR=            # optional, path to a fine-tuned NER model
VISION_MODEL_PATH=        # optional, path to a fine-tuned vision model
SESSION_COOKIE_NAME=aegis_session_id
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001"]
```

`frontend/.env.local` (optional — defaults to `http://localhost:8000`):
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Deployment

**Frontend (Vercel):** import the repo, root directory `frontend/`, set `NEXT_PUBLIC_API_BASE_URL` to the deployed backend's URL.

**Backend (Render or Railway):** deploy `backend/` (Dockerfile included) with a managed Postgres add-on. Same env vars as local dev, plus:
```
DATABASE_URL=<from the Postgres add-on>
CORS_ORIGINS=["https://<your-vercel-app>.vercel.app"]
```
The session cookie uses `samesite="none", secure=True` specifically so it survives the cross-origin Vercel↔Render/Railway hop — don't relax to `"lax"` unless frontend and backend end up sharing a domain.

---

## Project Structure

```
aegis/
├── backend/
│   ├── app/
│   │   ├── api/routers/       # ingestion.py, analysis.py, dashboard.py
│   │   ├── services/          # analysis, entity_extraction, ner_inference,
│   │   │                      # detection (vision), vision (OCR cascade),
│   │   │                      # spatial (DBSCAN), correlation, clustering,
│   │   │                      # similarity, geocode, graph, vulnerability,
│   │   │                      # conclusion, ingestion
│   │   ├── db/                # SQLAlchemy session + repository
│   │   ├── models/            # ORM models
│   │   └── core/config.py     # pydantic-settings
│   ├── ml_training/
│   │   ├── ner/                # weak labeling, hand-correction, training,
│   │   │                       # ONNX export, benchmark
│   │   ├── vision/              # dataset download, YOLOv8n training
│   │   └── COLAB.md            # step-by-step training instructions
│   ├── tests/                  # 63 pytest unit tests
│   └── docker-compose.yml
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

---

*Started as a solo project at YaleHack 2026. For educational and personal security purposes only.*
