# SignalScout AI

**Evidence-First Why-Now Engine**

> One-line pitch: The GTM intelligence tool that shows its work — every score is computable from a deterministic formula, every claim traces to a live web source, and live/mock/fallback status is visible per evidence row.

---

## Problem

Sales reps spend 2–4 hours manually researching each account before outreach.
Most of that research is stale, shallow, and untracked.
AI can automate it — but only if it has access to the live public web, and only if the output is auditable.

## Solution

SignalScout is a deep research agent for GTM teams:
1. Collects live public web signals (news, hiring, product moves, competitor intel) via Bright Data
2. Computes a deterministic **Why-Now Score** from explicit signal weights — not invented by the LLM
3. Synthesizes an evidence-first report via LLM (Claude or MiMo, depending on which provider key is configured — synthesis only, the LLM never touches the score)
4. Outputs an action pack: sales angles, cold email, LinkedIn message, discovery questions

Every claim traces to a source URL, a Bright Data tool, and a confidence level.
Every score is computable: `score = Σ weight(signal) × impact × confidence_boost × mode_multiplier`.
Live/mock/fallback status is visible per evidence row — no hidden black box.

**Positioning: this is not another AI sales dashboard. It is an auditable GTM timing engine.**

## Why Bright Data is essential

Without Bright Data:
- News is stale (cached data days old)
- LinkedIn job pages are bot-blocked
- JS-heavy company blogs are inaccessible
- SERP results are rate-limited and unstructured

With Bright Data:
- SERP API → live news + funding signals, structured JSON (fires live in `/analyze`)
- Web Unlocker → JS-rendered enterprise pages, paywall bypass (fires live in `/analyze` on top SERP URL)
- Web Scraper API → LinkedIn hiring data via pre-warmed dataset snapshots (snapshots refreshed by `/warmup` and `/scraper/refresh` out-of-band)
- MCP Server → spec-compliant JSON-RPC 2.0 endpoint at `/mcp` so any Claude / OpenAI / agent client can call our agent's tools

---

## Architecture

```
User input (company name)
       │
       ▼
FastAPI /analyze/stream (SSE)
       │
       ├── Bright Data SERP API ─────────── live news + funding + competitor evidence
       ├── Web Unlocker ─────────────────── live full article text from top SERP URL
       ├── Web Scraper snapshot ─────────── pre-warmed LinkedIn hiring data from disk
       └── MCP Server (JSON-RPC 2.0) ────── exposes our agent at /mcp to any MCP client
       │
       ▼
Deterministic Scoring Engine
(signal weights → why-now score + breakdown)
       │
       ▼
LLM Synthesis — Claude or MiMo (optional overlay)
(executive summary + why-now reason + action pack)
       │
       ▼
AnalyzeResponse → Frontend Cockpit
```

**Mock-safe by default.** Every live call has a graceful fallback to demo data.
The cockpit always renders — demo cannot crash.

---

## Runtime modes

| Mode       | SERP API  | Claude     | When                                   |
|------------|-----------|------------|----------------------------------------|
| `live`     | live      | live       | Both API keys set, all calls succeed   |
| `hybrid`   | live/mock | live       | SERP live + Claude live, or partial    |
| `fallback` | attempted | —          | Live call failed, mock used            |
| `mock`     | mock      | mock       | No keys set (default, demo-safe)       |

Each evidence row in the ledger shows its own mode: **live**, **demo**, or **fallback**.

---

## Tools used (runtime behavior)

| Tool                  | Purpose                                                 | Status in `/analyze`           |
|-----------------------|---------------------------------------------------------|-------------------------------|
| SERP API (news)       | Funding / launch / product signals                      | **Live in request**           |
| SERP API (competitor) | Competitor discovery via organic search                 | **Live in request**           |
| Web Unlocker          | Full article text + paywall/JS bypass on top SERP URL   | **Live in request**           |
| Web Scraper API       | LinkedIn hiring data (LinkedIn jobs dataset)            | **Pre-warmed snapshot** (loaded from disk; fresh dataset triggers run out-of-band via `/warmup` or `/scraper/refresh`) |
| MCP Server            | JSON-RPC 2.0 endpoint exposing our agent as tools       | **Live at `/mcp`**            |
| LLM synthesis         | Executive summary + why-now reason + (optional) action pack | **Live — Claude or MiMo** (whichever provider key is configured; cascade falls back to deterministic templates) |

> **Important truthfulness note**: `/analyze` does NOT trigger a fresh Web
> Scraper dataset job per request — Bright Data Web Scraper jobs are async
> (1-5 min) and would break the 3-minute demo flow. Snapshots are pre-warmed
> overnight (or by hand via `/warmup` / `/scraper/refresh`) and served from
> disk during a request. This is the standard enterprise pattern (Salesforce,
> Outreach, ZoomInfo do the same for LinkedIn data on CRM accounts).

---

## Quickstart

### Prerequisites
- Python 3.11+
- Node 18+

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## Environment variables

```env
# backend/.env

# Bright Data (leave empty to use mock mode — demo-safe)
BRIGHT_DATA_API_TOKEN=
BRIGHT_DATA_SERP_ZONE=serp_api1
BRIGHT_DATA_UNLOCKER_ZONE=web_unlocker1
BRIGHT_DATA_SCRAPER_DATASET_ID=     # optional — /analyze still serves pre-warmed snapshots without it

# LLM cascade — Claude (primary) → MiMo (failover) → deterministic templates
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
ANTHROPIC_MAX_TOKENS=1200
MIMO_API_KEY=
MIMO_BASE_URL=https://api.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5

# Mode flags
USE_MOCK=true        # set "false" once tokens are filled to enable live calls
FAST_DEMO=false      # set "true" in production to shorten SSE timeline delays
AUTO_WARMUP=false    # set "true" in production to pre-cache hero companies on boot
```

---

## Scoring engine

Scores are **not generated by the LLM**. They are computed deterministically:

```
for each signal in report:
  weight   = SIGNAL_WEIGHTS[signal.kind][dimension]
  impact   = IMPACT_MULTIPLIER[signal.impact]      # positive=1.0, negative=0.4
  boost    = CONFIDENCE_BOOST[evidence.confidence] # high=1.0, medium=0.85
  mode_adj = MODE_MULTIPLIER[evidence.mode]        # live=1.2x, mock=1.0x

  score_dim += 100 × weight × impact × boost × mode_adj
```

Live evidence gets a 20% boost over mock, so the score rises when real data is connected.
The **Why-Now Score Breakdown** section in the UI shows each component.

---

## Evidence ledger

Every insight has an evidence row with:
- `source` — domain or service
- `source_title` — actual article/page headline
- `url` — link to original (when available)
- `signal` — detected signal type (hiring, funding, product, etc.)
- `tool` — Bright Data tool that collected it
- `confidence` — low / medium / high
- `mode` — **live** / demo / fallback (visible per row)
- `timestamp` — when available from source

If mode is `demo`, all summaries are labeled `[DEMO]` so judges can tell.

---

## Limitations

- Web Scraper API is **not triggered synchronously** in `/analyze`. It serves
  pre-warmed snapshots from disk. Fresh dataset jobs run out-of-band via
  `/warmup` or `/scraper/refresh`. This is intentional — dataset trigger+poll
  takes 1-5 minutes and would block live demos. Honest UI labels everywhere.
- Company profile fields (industry, HQ, size) are intentionally hidden in
  live mode rather than fabricated. Only `name` and `domain` are shown.
- No persistence layer — each `/analyze` is stateless beyond an in-memory cache.
- SERP signal classification uses keyword matching, not NLP. Works well in
  practice for the eight signal kinds we support.

## What is intentionally not built

- No auth / login
- No vector DB / RAG
- No CRM integration
- No fine-tuning
- No multi-agent swarm
- No microservices

**One killer workflow done well > five workflows half-shipped.**

---

## Deployment (Vercel + Google Cloud Run)

This project is currently deployed at:
- **Frontend:** https://signalscout-ai.vercel.app
- **Backend:** https://signalscout-api-47232592262.asia-southeast2.run.app
- **GitHub:** https://github.com/whard2205/signalscout-ai

`backend/Dockerfile`, `backend/.dockerignore`, and `railway.json` are committed
so you can deploy to **Cloud Run**, **Railway**, or **Render** without code
changes. The instructions below cover the live setup (Cloud Run + Vercel) plus
fallbacks in the call-out box at the top of [DEPLOY.md](DEPLOY.md).

### Backend (Google Cloud Run)

Cloud Run was chosen because the free tier is **always-on (no cold-start
sleep)** unlike Render free, which matters for live demos.

```bash
# One-time setup
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
gcloud config set project <your-project-id>

# Deploy from source (uses backend/Dockerfile)
gcloud run deploy signalscout-api \
  --source backend \
  --region asia-southeast2 \
  --allow-unauthenticated \
  --memory 512Mi --cpu 1 --timeout 300 --port 8080
```

Then set env vars (non-secrets safe to put inline):

```bash
gcloud run services update signalscout-api --region asia-southeast2 --update-env-vars \
  BRIGHT_DATA_SERP_ZONE=serp_api1,\
  BRIGHT_DATA_UNLOCKER_ZONE=web_unlocker1,\
  ANTHROPIC_MODEL=claude-haiku-4-5-20251001,\
  ANTHROPIC_MAX_TOKENS=1200,\
  MIMO_BASE_URL=https://api.xiaomimimo.com/v1,\
  MIMO_MODEL=mimo-v2.5,\
  USE_MOCK=false,\
  FAST_DEMO=true,\
  AUTO_WARMUP=true
```

Secrets via a temporary YAML so they don't appear in shell history — see
[`DEPLOY.md`](DEPLOY.md) for the exact script. Required secrets:

- `BRIGHT_DATA_API_TOKEN`
- `BRIGHT_DATA_SCRAPER_DATASET_ID` (optional — `/analyze` serves pre-warmed snapshots without it)
- `ANTHROPIC_API_KEY`
- `MIMO_API_KEY`

Smoke test:

```bash
curl https://<your-cloud-run-url>/health
# {"status":"ok","mode":"live","claude":"configured","mimo":"configured","version":"0.4.0"}
```

`AUTO_WARMUP=true` pre-caches the 6 hero companies right after boot — first
real demo click then returns in ~6 ms.

### Frontend (Vercel)

1. Vercel → New Project → import this repo, root directory `frontend/`.
2. **Required env var** (Project → Settings → Environment Variables):
   - `NEXT_PUBLIC_API_BASE` = `https://<your-backend-url>`  ← Cloud Run URL, no trailing slash
3. Deploy.

> **Important**: without `NEXT_PUBLIC_API_BASE`, the deployed Vercel app cannot
> reach the backend. The local-dev `/api → localhost:8000` rewrite is
> auto-disabled in production builds (see `next.config.js`). If you forget,
> you'll see a console warning in the browser.

### Web Scraper snapshots

Snapshots under `backend/snapshots/*.json` are committed to the repo so the
Docker image bakes them in and serves them after boot. To refresh:

```bash
# Trigger fresh Bright Data Web Scraper jobs (requires BRIGHT_DATA_SCRAPER_DATASET_ID):
curl -X POST https://<your-cloud-run-url>/scraper/refresh
```

The `Web Scraper API` row in the cockpit shows **"pre-warmed Bright Data Web
Scraper snapshot"** — we never claim a synchronous live scrape because dataset
trigger + poll is async (1-5 min) and would break the 3-minute demo flow.
Pre-warming overnight is the production pattern (same as Salesforce, Outreach,
ZoomInfo do for enterprise accounts).

### Fallback platforms

`backend/Dockerfile` + `railway.json` make the same image deployable on:
- **Railway** — push to GitHub, import in Railway dashboard, set env vars
- **Render** — connect repo, set root `backend/`, build `pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0 --port $PORT`

See [DEPLOY.md](DEPLOY.md) §"Railway fallback" and §"Google Cloud Run fallback" for full instructions.

---

Built for [Bright Data Web Data UNLOCKED Hackathon](https://brightdata.com) · May 25–31, 2026
