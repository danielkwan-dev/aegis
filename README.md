# Aegis | Personal Privacy Intelligence Shield
### YHack 2026 Finalist @ Yale University

# Devpost
https://devpost.com/software/aegis-68rmo0

# Authors
Daniel Kwan (@danielkwan-dev)

# About

Aegis is a real-time OSINT (Open-Source Intelligence) and machine learning tool that detects **Identity Links** — cross-post patterns of location, time, and activity that allow a threat actor to reconstruct your daily routine from public social media alone.

---
# Demo
https://youtu.be/Nf_50lff9Rc

## The Problem

Standard security tooling covers network intrusion, malware, and credential theft. Nothing addresses the slow-burn threat of behavioral pattern exposure through social media. A motivated adversary — stalker, investigator, or state actor — does not need to compromise a single system. They just need to read your feed.

---

## Machine Learning Pipeline

1. **Signal Extraction** — Named entity recognition (regex + domain lexicon) pulls streets, landmarks, businesses, and temporal expressions from post text. Tesseract OCR extracts text from image backgrounds. Pillow pulls GPS coordinates and timestamps from EXIF metadata.

2. **Baseline Corpus** — All scraped posts are ingested into an in-memory UserFootprint document store, which becomes the training corpus for threat detection.

3. **TF-IDF Similarity Scoring** — Three independent TF-IDF vectorizers (locations, timestamps, activities) are trained on the baseline corpus. A draft post is transformed into the same vector space and scored via cosine similarity against every baseline document, producing a weighted breach probability score (0–100%).

4. **Entity Triplet Detection** — Co-occurrence analysis identifies recurring (time, location, activity) triplets across posts. Triplets with consistent timing are classified as static landmarks — high-confidence predictions of where the subject will be and when.

5. **KMeans Routine Clustering** — Baseline posts are clustered on extracted feature vectors to identify distinct behavioral routines and score each for temporal predictability.

6. **Vulnerability Map** — Each detected pattern becomes a structured finding: severity rating (Critical / High / Medium / Low), evidence count, and quantified risk reduction showing exactly how much the score drops if a specific signal is removed.

---

## Cybersecurity Threat Model

| Adversary | What Aegis Detects |
|-----------|-------------------|
| Stalker / Harasser | Home neighbourhood, daily schedule, recurring locations |
| Corporate Investigator | Workplace, travel patterns, relationship network |
| State-Level Actor | Full behavioral profile, vulnerability windows, predictive location |

**Attack vectors modelled:**
- Location triangulation from cross-post geography
- Temporal pattern analysis from posting time consistency
- OCR side-channel — location data embedded in image backgrounds
- EXIF geolocation — GPS coordinates in image metadata
- Routine prediction from historical behavioral anchors

---

## Key Features

- OSINT scraping — Instagram via Instaloader, OCR via Tesseract, EXIF via Pillow
- TF-IDF cosine similarity threat scoring across three signal categories
- KMeans behavioral clustering and entity triplet detection
- Hex.tech API integration — automated intelligence brief on every analysis run and "Stalker's Web" graph of entity relationships
- Async background processing — results return in under one second
- Persistent breach probability history via JSONBlob

---

## Tech Stack

**Machine Learning**
- scikit-learn 1.6 — TF-IDF vectorization, cosine similarity, KMeans
- NumPy 2.2 — feature vector construction
- Pytesseract 0.3 — OCR pipeline
- Pillow 11.1 — image processing, EXIF extraction

**Backend**
- FastAPI 0.111 + Uvicorn 0.29
- Instaloader 4.13 — Instagram scraping
- httpx — async HTTP for Hex API and JSONBlob

**Frontend**
- Next.js 14.2, TypeScript 5.4
- Framer Motion, react-force-graph-2d, Canvas API

**External Services**
- Hex.tech — automated notebook runs via API, embedded OPSEC dashboard
- JSONBlob — serverless JSON persistence

---

## Getting Started

**Prerequisites:** Node.js 18+, Python 3.11+, Tesseract OCR installed locally

```bash
# Backend
cd backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install && npm run dev
```

Create `backend/.env`:
```
HEX_API_TOKEN=your_hex_api_token
HEX_PROJECT_ID=your_hex_project_id
JSONBLOB_ID=                  # auto-created on first run
HISTORY_BLOB_ID=              # auto-created on first run
```

---

## Demo Mode

Use handle **`@aegis_yhack`** — no real Instagram account needed. Then analyze:

> "Grabbing my usual morning coffee down on Market Street"

Triggers a Critical-level breach detection showing how one sentence, cross-referenced against a baseline corpus, reconstructs a full daily routine.

---

## Project Structure

```
aegis/
├── backend/
│   ├── main.py        # FastAPI endpoints, background tasks
│   ├── engine.py      # ML threat analysis engine (~1800 lines)
│   ├── instagram.py   # Instagram scraping
│   └── demo.py        # Pre-loaded demo data
└── frontend/
    └── components/
        ├── SimulateForm.tsx      # Instagram sync + analysis
        ├── AuditResult.tsx       # Threat report
        ├── HexDashboard.tsx      # Hex embed panel
        ├── StalkerWeb.tsx        # Entity relationship graph
        ├── MatrixRain.tsx        # Animated side panels
        ├── RiskGauge.tsx         # Breach probability gauge
        └── ScoreTracker.tsx      # Score history
```

---

**YaleHack 2026 — Solo project by Daniel Kwan**

*For educational and personal security purposes only.*
