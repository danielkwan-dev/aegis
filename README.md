# Aegis | Personal Privacy Intelligence Engine

Aegis detects **Identity Links** — cross-post patterns of location, time, and activity that let a threat actor reconstruct someone's daily routine from public social media posts alone. It started as a solo hackathon project and has since been rebuilt from the ground up into a real, tested, fine-tuned-ML system.

**Devpost:** https://devpost.com/software/aegis-68rmo0

**Hackathon Demo Video:** https://youtu.be/Nf_50lff9Rc
*(This demo shows the original YHack 2026 hackathon build — live Instagram scraping, a Hex.tech-embedded dashboard, JSONBlob persistence. The architecture below reflects a full post-hackathon rebuild; see [What changed since the hackathon](#what-changed-since-the-hackathon).)*

**Author:** Daniel Kwan ([@danielkwan-dev](https://github.com/danielkwan-dev))

---

## The Problem

Standard security tooling covers network intrusion, malware, and credential theft. Nothing addresses the slow-burn threat of behavioral pattern exposure through social media. A motivated adversary — stalker, investigator, or state actor — doesn't need to compromise a system. They just need to read a feed.

| Adversary | What Aegis Detects |
|---|---|
| Stalker / Harasser | Home neighbourhood, daily schedule, recurring locations |
| Corporate Investigator | Workplace, travel patterns, relationship network |
| State-Level Actor | Full behavioral profile, vulnerability windows, predictive location |

**Attack vectors modeled:**
- Location triangulation from cross-post geography
- Temporal pattern analysis from posting-time consistency
- OCR side-channel — location data embedded in image backgrounds (street signs, storefronts)
- EXIF geolocation — GPS coordinates embedded in image metadata
- Routine prediction from historical behavioral anchors

---

## Machine Learning Pipeline

1. **Entity extraction** — a fine-tuned **DistilBERT** token-classification model (streets, landmarks, businesses, times, activities), trained via weak supervision and hand-corrected gold labels. Falls back automatically to the original regex/keyword extractor when no trained model is configured, so the app is never non-functional.
2. **Vision cascade** — a fine-tuned **YOLOv8n** signage/storefront detector runs a full **detect → crop → preprocess → OCR → NER** pipeline: find signage in a photo, crop and contrast-enhance each region, OCR each crop individually (sharper than OCR-ing the whole image), then run entity extraction on the result.
3. **EXIF + OCR signal fusion** — Pillow extracts GPS/timestamp metadata; Tesseract OCR reads any text baked into an image.
4. **Geocoding** — free-text locations resolved to coordinates via Nominatim (OpenStreetMap), Postgres-cached to respect rate limits.
5. **Geospatial risk clustering** — DBSCAN + Haversine distance clusters GPS coordinates into two distinct signal types: dense repeat-visit clusters ("**Routine Exposure**" — predictable, high risk) vs. one-off outliers ("**Anomalous Disclosure**" — informationally sensitive but not a pattern). These are deliberately not conflated into one score.
6. **TF-IDF similarity scoring** — three independent TF-IDF vectorizers (locations, timestamps, activities), cosine-similarity-scored against a session's baseline post history to produce a weighted breach-probability score (0–100%).
7. **Entity triplet detection** — co-occurrence analysis finds recurring (time, location, activity) triplets across posts; consistent-timing triplets become static-landmark findings.
8. **K-Means routine clustering** — baseline posts clustered on extracted feature vectors to identify distinct behavioral routines and their temporal predictability.
9. **Vulnerability map + conclusion narrative** — every detected pattern becomes a structured finding (severity, evidence count, risk-reduction-if-removed), synthesized into a readable narrative.

### Trained model results

| Model | Metric | Result | Deployed size |
|---|---|---|---|
| NER (DistilBERT, fine-tuned) | Entity F1 | 0.851 | 265.6MB |
| NER (int8 quantized, ONNX) | Entity F1 | 0.832 | **66.8MB** (4.0x smaller, ~34% faster) |
| Vision (YOLOv8n, fine-tuned) | mAP50 / mAP50-95 | 0.567 / 0.333 | 12.3MB |
| Vision (int8 quantized, ONNX) | — | — | **3.4MB** (3.6x smaller) |

NER per-category F1: STREET 0.883, TIME 0.923, BUSINESS 0.900, ACTIVITY 0.859, LANDMARK 0.273 (weak — only 26 gold examples for that category, a known limitation). Both models were trained on a free Colab T4 GPU, exported to ONNX, quantized, and are served via `onnxruntime` — the serving app never depends on `torch`/`transformers` at request time, only at training time.

Both models degrade gracefully: if no trained weights are configured, the app automatically falls back to the regex baseline (NER) or whole-image OCR (vision) — it's fully functional either way, just less accurate.

Full training pipeline (weak-label bootstrapping, hand-correction workflow, Colab training steps) documented in [`backend/ml_training/COLAB.md`](backend/ml_training/COLAB.md).

---

## Architecture

- **Backend**: Python, FastAPI, layered architecture (`api/` routers → `services/` business logic → `db/`/`models/` persistence), PostgreSQL via SQLAlchemy, Docker Compose for local dev. Per-session state (not a global in-memory store) — each analysis session's footprint is scoped and persisted.
- **Frontend**: Next.js 14, TypeScript, TailwindCSS, Framer Motion, `react-force-graph-2d` for the entity-relationship "Stalker's Web" graph.
- **Testing**: 61 pytest unit tests. ML inference, external HTTP calls, and geospatial math are all dependency-injected and unit-testable without live models, weights, or network access.

### Data ingestion — no live scraping

The original hackathon build scraped live Instagram profiles via Instaloader, which violates Instagram's Terms of Service. That's gone. Ingestion is now:
- **Official data export** — upload your own Instagram "Download Your Data" `.zip`, parsed and bulk-ingested (`/api/ingest/export`).
- **Manual entry** — a single caption/photo for live demos (`/api/ingest/manual`).

---

## What changed since the hackathon

Aegis won YHack 2026, but the original build had real hackathon debt: hardcoded coordinate lookups, a hardcoded Tesseract path, a canned-response demo mode, two third-party sponsor-tool dependencies (Hex.tech, JSONBlob) standing in for a real database, a dead duplicate frontend scaffold, and live Instagram scraping. Everything above reflects a deliberate rebuild:

| Area | Hackathon build | Current build |
|---|---|---|
| Data ingestion | Live Instagram scraping (Instaloader) | Official data export + manual entry (ToS-compliant) |
| Entity extraction | Regex + hardcoded lexicon only | Fine-tuned DistilBERT NER, regex as fallback |
| Image signal extraction | Whole-image OCR only | YOLOv8-detected crops → OCR → NER cascade |
| Geospatial clustering | Fixed-degree coordinate bucketing | DBSCAN + Haversine, dual risk signals |
| Location resolution | Hardcoded 10-entry coordinate dict | Nominatim geocoding, Postgres-cached |
| Persistence | In-memory store + JSONBlob | PostgreSQL |
| Analytics dashboard | Hex.tech notebook embed (backend round-trip) | Backend dependency fully removed — analysis runs synchronously, no external call |
| Testing | None | 61 unit tests |

This frontend rebuild removed the orphaned `HexDashboard.tsx` entirely and replaced it with an in-house UI (see `docs/superpowers/specs/2026-08-21-frontend-rebuild-design.md`). Every item in the table above is now done.

---

## Tech Stack

**Serving app (backend)**
- FastAPI, Uvicorn, SQLAlchemy, PostgreSQL, Docker Compose
- `onnxruntime` + `tokenizers` — ML inference (deliberately no `torch`/`transformers` at serving time)
- `pytesseract` + Pillow — OCR and EXIF extraction
- `httpx` — Nominatim geocoding client
- scikit-learn, NumPy — TF-IDF similarity, K-Means clustering, DBSCAN spatial clustering

**ML training** (`backend/ml_training/`, separate venv — not a serving dependency)
- `transformers`, `accelerate`, `datasets`, `seqeval` — DistilBERT fine-tuning
- `ultralytics`, `roboflow` — YOLOv8n fine-tuning
- `optimum[onnxruntime]` — ONNX export + int8 quantization
- Trained on Google Colab (free T4 GPU), models published to Hugging Face Hub

**Frontend**
- Next.js 14, TypeScript, TailwindCSS, Framer Motion, `react-force-graph-2d`

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
│   ├── tests/                  # 61 pytest unit tests
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
