# Aegis — Personal Privacy Intelligence Engine
### YaleHack 2026 · Solo Project by Daniel Kwan

> *"We don't need to hack your phone. We just need to read your Instagram."*

Aegis is a real-time OSINT-powered cybersecurity tool that applies machine learning to detect **Identity Links** — the cross-post patterns of location, time, and activity data that allow a threat actor to fully reconstruct your daily routine from public social media alone. Built in 36 hours as a solo project for YaleHack 2026.

The core insight: individual posts are not the vulnerability. The **statistical pattern across dozens of posts** is. Aegis models that pattern the same way an adversary would — then warns you before you publish.

---

## The Problem

Open-source intelligence (OSINT) is one of the most effective and underestimated attack vectors in modern cybersecurity. A sufficiently motivated adversary — stalker, corporate spy, or nation-state actor — does not need to compromise a single system to locate and profile a target. They need only read a public Instagram feed.

Standard security tooling addresses network intrusion, malware, and credential theft. No tool exists that addresses the passive, slow-burn threat of **behavioral pattern exposure through social media**. Aegis fills that gap.

---

## Machine Learning Pipeline

The threat detection engine is built around a multi-stage NLP and machine learning pipeline, implemented from scratch using scikit-learn.

### Stage 1 — Signal Extraction

Raw post text and images are processed through three parallel extraction pipelines:

- **Named Entity Recognition (regex + domain lexicon)** — Extracts street names, landmarks, businesses, and coordinates using a combination of suffix-pattern matching (St, Ave, Blvd, etc.) and a curated gazetteer of known locations
- **OCR Entity Detection (Tesseract + Pillow)** — Images are run through Tesseract OCR to extract text embedded in photos — street signs, storefronts, receipts — that the post caption never mentions but the image reveals
- **EXIF Metadata Extraction** — GPS coordinates, timestamps, and device fingerprints are pulled from image metadata, converting a seemingly harmless photo into a precise geolocation event
- **Temporal Signal Parsing** — Time-of-day references, day-of-week patterns, and recurring schedule language are extracted and normalised into time context vectors

### Stage 2 — Baseline Corpus Construction

All scraped posts are ingested into a **UserFootprint** — an in-memory document store that maintains the full history of extracted signals. This corpus becomes the training data against which new posts are evaluated.

### Stage 3 — TF-IDF Similarity Scoring

The core threat detection model uses **category-specific TF-IDF vectorization** with cosine similarity:

- Three independent TF-IDF vectorizers are trained — one per signal category (locations, timestamps, activities)
- The baseline corpus is fit-transformed into a per-category document matrix
- A draft post is transformed into the same vector space
- Cosine similarity is computed between the draft vector and every baseline document per category
- Per-category similarity scores are weighted and combined into a single **breach probability score** (0–100%)

This approach is deliberately modelled on how real OSINT analysts reason: not "does this post contain dangerous information" but "does this post, in the context of everything else this person has posted, complete a pattern that reveals their routine."

### Stage 4 — Routine Correlation and Entity Triplet Detection

Beyond similarity scoring, the engine runs a **co-occurrence analysis** to detect recurring `(time, location, activity)` triplets across the baseline corpus. A triplet that appears with consistent timing across multiple posts is classified as a **static landmark** — a high-confidence prediction of where the subject will be and when. This is the same inference methodology used in real-world OSINT profiling.

### Stage 5 — KMeans Routine Clustering

Baseline posts are clustered using **KMeans** on extracted feature vectors to identify distinct behavioral routines (morning routine, lunch pattern, evening commute, etc.). Each cluster is labelled and scored for temporal consistency, giving the vulnerability map a structured view of which routines are most predictable.

### Stage 6 — Vulnerability Map Generation

Each detected pattern is converted into a structured vulnerability finding with:
- **Severity rating** (Critical / High / Medium / Low) based on evidence count, signal specificity, and category weight
- **Evidence citations** — specific baseline posts that support the finding
- **Quantified risk reduction** — if the user removes a specific signal from their draft, the engine recomputes the score and reports the exact percentage drop

---

## Cybersecurity Threat Model

Aegis models three distinct adversary profiles:

| Adversary | Capability | What Aegis Detects |
|-----------|-----------|-------------------|
| **Stalker / Harasser** | Low — manual OSINT, free tools | Home neighbourhood, daily schedule, recurring locations |
| **Corporate Investigator** | Medium — automated scraping, link analysis | Relationship network, workplace, travel patterns, income signals |
| **State-Level Actor** | High — persistent monitoring, cross-platform correlation | Full behavioral profile, vulnerability windows, predictive location |

The threat model is grounded in real OSINT methodology. The attack surface Aegis addresses is the **aggregation problem**: no single post is dangerous, but the union of all posts creates a high-fidelity target profile that bypasses all traditional security controls.

### Attack Vectors Modelled

- **Location triangulation** — Cross-referencing post locations over time to infer home, workplace, and commute route
- **Temporal pattern analysis** — Identifying consistent posting times to establish a target's daily schedule
- **OCR side-channel** — Extracting location data from image backgrounds that the poster did not consciously share
- **EXIF geolocation** — Recovering GPS coordinates from image metadata, bypassing any caption-level redaction
- **Routine prediction** — Using historical patterns to predict future physical location with high confidence
- **Social graph inference** — Identifying frequent co-appearances to map relationship networks

---

## Key Features

- **OSINT Data Collection** — Automated Instagram scraping via Instaloader; OCR on images via Tesseract; EXIF GPS and timestamp extraction via Pillow
- **NLP Entity Extraction** — Regex-based named entity recognition with domain-specific lexicons for streets, landmarks, businesses, and temporal expressions
- **TF-IDF Threat Scoring** — Per-category cosine similarity model producing a calibrated breach probability score
- **KMeans Routine Clustering** — Unsupervised clustering of behavioral patterns into labelled routine profiles
- **Entity Triplet Detection** — Co-occurrence analysis identifying high-confidence (time, location, activity) behavioral anchors
- **Vulnerability Map** — Structured security findings with severity ratings, evidence counts, and quantified remediation impact
- **Stalker's Web** — Force-directed graph visualising the entity relationship network extracted from post history
- **Hex.tech Intelligence Brief** — Every analysis triggers an automated Hex notebook run via API, generating a CIA-style OPSEC playbook
- **Async Background Processing** — Analysis results return in under one second; all external API calls fire asynchronously
- **Persistent Score History** — Breach probability is tracked across sessions via JSONBlob, enabling longitudinal risk monitoring

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js Frontend                        │
│  SimulateForm → AuditResult → HexDashboard + MatrixRain     │
│  VisualizationWrapper → StalkerWeb (force-directed graph)   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP (localhost:8000)
┌────────────────────────▼────────────────────────────────────┐
│                    FastAPI Backend                           │
│                                                             │
│  /api/sync-instagram  →  Instaloader + OCR + EXIF           │
│  /api/analyze-threat  →  ML Engine + Background Hex trigger │
│  /api/hex-run-status  →  Hex API polling                    │
│  /api/score-history   →  JSONBlob persistence               │
└──────────┬──────────────────────┬───────────────────────────┘
           │                      │
┌──────────▼──────────┐  ┌───────▼──────────────────────────┐
│   engine.py (ML)    │  │         External Services        │
│                     │  │                                  │
│  TF-IDF Vectorizer  │  │  Hex.tech  — notebook API runs   │
│  Cosine Similarity  │  │  JSONBlob  — data persistence    │
│  KMeans Clustering  │  │  Instaloader — IG scraping       │
│  Entity Extraction  │  │  Tesseract — OCR pipeline        │
│  Triplet Detection  │  └──────────────────────────────────┘
│  Vuln Map Generator │
└─────────────────────┘
```

---

## Tech Stack

### Machine Learning / Data Science
| Library | Version | Role |
|---------|---------|------|
| scikit-learn | 1.6 | TF-IDF vectorization, cosine similarity, KMeans clustering |
| NumPy | 2.2 | Feature vector construction, numerical scoring |
| Pytesseract | 0.3 | OCR pipeline for image text extraction |
| Pillow | 11.1 | Image processing, EXIF metadata extraction |

### Backend
| Technology | Version | Role |
|-----------|---------|------|
| FastAPI | 0.111 | Async REST API, background task management |
| Uvicorn | 0.29 | ASGI server |
| Instaloader | 4.13 | Instagram profile and post scraping |
| httpx | — | Async HTTP client for Hex API and JSONBlob |
| python-dotenv | — | Environment variable management |

### Frontend
| Technology | Version | Role |
|-----------|---------|------|
| Next.js | 14.2 | React framework, App Router |
| TypeScript | 5.4 | Type safety |
| Framer Motion | 12.38 | Animations |
| react-force-graph-2d | 1.29 | Entity relationship graph |
| Canvas API | — | Matrix rain side panels |
| Tailwind CSS | 4.2 | Utility styling |

### External Services
| Service | Role |
|---------|------|
| Hex.tech | Automated notebook runs via API; embedded OPSEC intelligence brief |
| JSONBlob.com | Serverless JSON store for dashboard payloads and score history |
| Tesseract OCR | Local OCR engine |

---

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed locally
- A Hex.tech account with a project configured

### 1. Clone the repo
```bash
git clone https://github.com/danielkwan-dev/aegis.git
cd aegis
```

### 2. Backend setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:
```
HEX_API_TOKEN=your_hex_api_token
HEX_PROJECT_ID=your_hex_project_id
JSONBLOB_ID=your_jsonblob_id          # optional, auto-created on first run
HISTORY_BLOB_ID=your_history_blob_id  # optional, auto-created on first run
```

Start the backend:
```bash
uvicorn main:app --reload --port 8000
```

### 3. Frontend setup
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HEX_API_TOKEN` | Yes | Hex.tech API token — Settings → API |
| `HEX_PROJECT_ID` | Yes | Hex project UUID |
| `JSONBLOB_ID` | No | Auto-created on first analysis run |
| `HISTORY_BLOB_ID` | No | Auto-created on first analysis run |
| `NEXT_PUBLIC_API_URL` | No | Backend URL, default `http://localhost:8000` |

---

## Project Structure

```
aegis/
├── backend/
│   ├── main.py          # FastAPI app, all API endpoints, background tasks
│   ├── engine.py        # ML threat analysis engine (~1800 lines)
│   ├── instagram.py     # Instagram scraping via Instaloader
│   ├── demo.py          # Pre-loaded demo mode
│   └── requirements.txt
│
└── frontend/
    ├── app/
    │   ├── page.tsx         # Main dashboard page
    │   ├── layout.tsx       # Root layout with MatrixRain
    │   └── globals.css      # Cyber-noir theme and keyframes
    └── components/
        ├── SimulateForm.tsx       # Instagram sync and analysis form
        ├── AuditResult.tsx        # Full threat report display
        ├── HexDashboard.tsx       # Hex embed panel
        ├── MatrixRain.tsx         # Animated canvas side panels
        ├── StalkerWeb.tsx         # Force-directed entity graph
        ├── VisualizationWrapper.tsx
        ├── RiskGauge.tsx          # SVG breach probability gauge
        ├── DigitalShadow.tsx      # Shadow scorecard
        ├── ScoreTracker.tsx       # Score history chart
        └── TypingEffect.tsx       # Animated text reveal
```

---

## Demo Mode

Use the handle **`@aegis_yhack`** to run a pre-loaded demo without a real Instagram account. After syncing, analyze this draft post:

> *"Grabbing my usual morning coffee on Market Street before work"*

This triggers a Critical-level breach detection, demonstrating how the ML pipeline cross-references a single innocuous sentence against a baseline corpus to reconstruct a full daily routine.

---

## Built For

**YaleHack 2026** — Solo project by **Daniel Kwan**

Built in 36 hours. No sleep. Maximum breach probability.

---

*Aegis Privacy Intelligence Engine — For educational and personal security purposes only.*
