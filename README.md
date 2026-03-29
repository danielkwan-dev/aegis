# AEGIS — Personal Privacy Intelligence Engine
### YaleHack 2026 · Solo Project by Daniel Kwan

> *"We don't need to hack your phone. We just need to read your Instagram."*

Aegis is a real-time personal security audit tool that detects **Identity Links** in your social media posts — combinations of location, time, and activity patterns that, when cross-referenced against your posting history, allow anyone to predict your daily routine. Built in 36 hours as a solo project for YaleHack 2026.

---

## What It Does

Most people don't get doxxed from a single post. They get doxxed from the **pattern across 30 posts**. Aegis catches that before you hit publish.

1. **Scrape** — Enter any public Instagram handle. Aegis scrapes their posts, runs OCR on images to extract text from signs and backgrounds, pulls EXIF GPS metadata from photos, and builds a complete exposure map of their digital footprint.

2. **Analyze** — Paste a draft post (with optional image). Aegis runs it against the scraped baseline using TF-IDF cosine similarity across three signal categories — locations, timestamps, and activities — to detect Identity Links that connect your draft to your existing pattern.

3. **Report** — Get a full breach probability score, vulnerability map with severity ratings (Critical / High / Medium / Low), entity triplets showing exactly what routine is exposed, and specific risk reduction recommendations showing how much each change drops your score.

4. **Dashboard** — Every analysis triggers a live Hex.tech intelligence brief — a CIA-style privacy playbook with pre-post checklists, OPSEC protocols, and threat reduction tables.

---

## Key Features

- **Instagram OSINT** — Live scraping via Instaloader with OCR on images (Tesseract) and EXIF metadata extraction
- **TF-IDF Identity Linking** — Scikit-learn cosine similarity across location, time, and activity signal categories
- **Geographic Exposure Mapping** — Detects street names, landmarks, businesses and maps them to coordinates
- **Stalker's Web** — Force-directed graph showing how your posts connect through shared entities
- **Hex.tech Integration** — Automated API-triggered intelligence briefs on every analysis run
- **Risk Reduction Scenarios** — Quantified score drops for each specific recommendation
- **Matrix Rain UI** — Cyberpunk aesthetic with animated katakana/hex character side panels
- **Background Processing** — Analysis returns instantly; Hex runs fire asynchronously
- **Score History** — Persistent breach probability tracking across sessions via JSONBlob

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js Frontend                         │
│  SimulateForm → AuditResult → HexDashboard + MatrixRain     │
│  VisualizationWrapper → StalkerWeb (force graph)            │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP (localhost:8000)
┌────────────────────────▼────────────────────────────────────┐
│                    FastAPI Backend                           │
│                                                             │
│  /api/sync-instagram  →  Instaloader + OCR + EXIF           │
│  /api/analyze-threat  →  Engine + Background Hex trigger    │
│  /api/hex-run-status  →  Hex API polling                    │
│  /api/score-history   →  JSONBlob persistence               │
└──────────┬──────────────────────┬───────────────────────────┘
           │                      │
┌──────────▼──────────┐  ┌───────▼──────────────────────────┐
│   engine.py          │  │         External APIs            │
│                      │  │                                  │
│  • Entity extraction │  │  Hex.tech  — notebook runs       │
│  • TF-IDF similarity │  │  JSONBlob  — data persistence    │
│  • Routine detection │  │  Instaloader — IG scraping       │
│  • Vulnerability map │  │  Tesseract — OCR                 │
│  • Exposure graph    │  └──────────────────────────────────┘
└──────────────────────┘
```

---

## Tech Stack

### Frontend
| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 14.2 | React framework, App Router |
| TypeScript | 5.4 | Type safety |
| Framer Motion | 12.38 | Animations |
| react-force-graph-2d | 1.29 | Stalker's Web graph |
| Tailwind CSS | 4.2 | Utility styles |
| Canvas API | — | Matrix rain effect |

### Backend
| Technology | Version | Purpose |
|-----------|---------|---------|
| FastAPI | 0.111 | REST API + async endpoints |
| Uvicorn | 0.29 | ASGI server |
| Scikit-learn | 1.6 | TF-IDF vectorizer, cosine similarity, KMeans clustering |
| NumPy | 2.2 | Numerical operations |
| Pytesseract | 0.3 | OCR on images |
| Pillow | 11.1 | Image processing + EXIF extraction |
| Instaloader | 4.13 | Instagram profile scraping |
| httpx | — | Async HTTP (Hex API + JSONBlob) |
| python-dotenv | — | Environment variable management |

### External Services
| Service | Purpose |
|---------|---------|
| **Hex.tech** | Automated notebook runs via API, embedded intelligence brief |
| **JSONBlob.com** | Serverless JSON persistence for dashboard data + score history |
| **Tesseract OCR** | Local OCR engine for extracting text from images |

---

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) installed locally
- A Hex.tech account with a project set up

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
```env
HEX_API_TOKEN=your_hex_api_token
HEX_PROJECT_ID=your_hex_project_id
JSONBLOB_ID=your_jsonblob_id          # optional, created on first run
HISTORY_BLOB_ID=your_history_blob_id  # optional, created on first run
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
| `HEX_API_TOKEN` | Yes | Hex.tech API token (Settings → API) |
| `HEX_PROJECT_ID` | Yes | Your Hex project UUID |
| `JSONBLOB_ID` | No | Auto-created on first analysis run |
| `HISTORY_BLOB_ID` | No | Auto-created on first analysis run |
| `NEXT_PUBLIC_API_URL` | No | Backend URL (default: `http://localhost:8000`) |

---

## Project Structure

```
aegis/
├── backend/
│   ├── main.py          # FastAPI app, all API endpoints
│   ├── engine.py        # Core threat analysis engine (~1800 lines)
│   ├── instagram.py     # Instagram scraping via Instaloader
│   ├── demo.py          # Demo mode with preset data
│   └── requirements.txt
│
└── frontend/
    ├── app/
    │   ├── page.tsx         # Main dashboard page
    │   ├── layout.tsx       # Root layout + MatrixRain
    │   └── globals.css      # Cyber-noir theme + keyframes
    └── components/
        ├── SimulateForm.tsx       # Main form (Instagram sync + analysis)
        ├── AuditResult.tsx        # Full results display
        ├── HexDashboard.tsx       # Hex embed panel with demo cycle
        ├── MatrixRain.tsx         # Animated canvas side panels
        ├── StalkerWeb.tsx         # Force-directed exposure graph
        ├── VisualizationWrapper.tsx
        ├── RiskGauge.tsx          # SVG breach probability dial
        ├── DigitalShadow.tsx      # Shadow scorecard
        ├── ScoreTracker.tsx       # History chart
        └── TypingEffect.tsx       # Animated text reveal
```

---

## Demo Mode

Use the handle **`@aegis_yhack`** to run a pre-loaded demo without needing a real Instagram account. It simulates a scanned profile with realistic post data, then try analyzing this draft post:

> *"Grabbing my usual morning coffee on Market Street before work"*

This triggers a full Critical-level breach detection showing how a seemingly innocent post reveals a predictable routine.

---

## How the Engine Works

### Identity Link Detection
Aegis uses a three-category TF-IDF similarity model:

1. **Location signals** — Street names, landmarks, businesses extracted via regex + known entity lists
2. **Timestamp signals** — Time-of-day references, day patterns, recurring schedules
3. **Activity signals** — Keywords like commute, gym, coffee, lunch that establish behavioral patterns

Each category gets its own TF-IDF vectorizer trained on the user's baseline posts. The draft post is then scored against each category independently, producing a weighted breach probability.

### Routine Correlation
Beyond simple similarity, Aegis detects **entity triplets** — `(time, location, activity)` combinations that appear repeatedly across posts — using co-occurrence analysis to identify predictable routines. A triplet appearing 3+ times with consistent timing is flagged as a static landmark.

### Vulnerability Scoring
Each finding is scored by:
- **Evidence count** — how many baseline posts support the pattern
- **Category weight** — location > timestamp > activity
- **Specificity** — street-level > neighbourhood > city

---

## Built For

**YaleHack 2026** — Solo project by **Daniel Kwan**

Built in 36 hours. No sleep. Maximum breach probability.

---

*Aegis Privacy Intelligence Engine — For educational and personal security purposes only.*