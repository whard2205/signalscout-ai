# Deploy — Render (backend) + Vercel (frontend)

Hackathon deadline: **2026-05-31**. Optimized for the 3-minute live demo.

> **Railway fallback:** if Render billing/card verification blocks deployment,
> use Railway for the backend. `railway.json` is committed at repo root and
> runs:
> - Build: `cd backend && pip install -r requirements.txt`
> - Start: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
> - Healthcheck: `/health`
>
> Railway variables are the same as Render:
> `BRIGHT_DATA_API_TOKEN`, `BRIGHT_DATA_SERP_ZONE=serp_api1`,
> `BRIGHT_DATA_UNLOCKER_ZONE=web_unlocker1`,
> `BRIGHT_DATA_SCRAPER_DATASET_ID`, `ANTHROPIC_API_KEY`,
> `ANTHROPIC_MODEL=claude-haiku-4-5-20251001`,
> `ANTHROPIC_MAX_TOKENS=1200`, `LLM_TIMEOUT_S=18`, `MIMO_API_KEY`,
> `MIMO_BASE_URL=https://api.xiaomimimo.com/v1`, `MIMO_MODEL=mimo-v2.5`,
> `USE_MOCK=false`, `FAST_DEMO=true`, `AUTO_WARMUP=true`,
> `ANALYZE_TIMEOUT_S=60`,
> `PYTHON_VERSION=3.11.9`.
>
> After Railway deploy, generate a public domain and set Vercel
> `NEXT_PUBLIC_API_BASE=https://<railway-domain>`.

> **Google Cloud Run fallback:** if Render/Railway/Koyeb billing blocks you,
> deploy the backend to Cloud Run. `backend/Dockerfile` is committed and listens
> on Cloud Run's injected `$PORT`.
>
> From Google Cloud Shell:
> ```
> gcloud services enable run.googleapis.com cloudbuild.googleapis.com
> gcloud run deploy signalscout-api --source backend --region asia-southeast2 --allow-unauthenticated
> ```
>
> Then Cloud Run service -> Edit & deploy new revision -> Variables and Secrets:
> `BRIGHT_DATA_API_TOKEN`, `BRIGHT_DATA_SERP_ZONE=serp_api1`,
> `BRIGHT_DATA_UNLOCKER_ZONE=web_unlocker1`, `BRIGHT_DATA_SCRAPER_DATASET_ID`,
> `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL=claude-haiku-4-5-20251001`,
> `ANTHROPIC_MAX_TOKENS=1200`, `LLM_TIMEOUT_S=18`, `MIMO_API_KEY`,
> `MIMO_BASE_URL=https://api.xiaomimimo.com/v1`, `MIMO_MODEL=mimo-v2.5`,
> `USE_MOCK=false`, `FAST_DEMO=true`, `AUTO_WARMUP=true`,
> `ANALYZE_TIMEOUT_S=60`.
>
> Smoke test: `https://<cloud-run-url>/health`, then set Vercel
> `NEXT_PUBLIC_API_BASE=https://<cloud-run-url>`.

> **DO NOT commit secrets.** `backend/.env` and `frontend/.env.local` are
> already covered by `.gitignore`. Verify before each push:
> ```
> git ls-files | findstr /R "\.env$ \.env\." | findstr /V "example"
> ```
> Expected output: empty.

---

## 0 · Prerequisites

- Render account: <https://dashboard.render.com>
- Vercel account: <https://vercel.com/dashboard>
- A GitHub repo with this codebase pushed (the local git repo is set up;
  push to GitHub before continuing).

```powershell
# One-time: create GitHub repo and push
gh repo create signalscout-ai --public --source=. --remote=origin --push
```

---

## 1 · Render — Backend (FastAPI)

### Service settings

| Field             | Value                                                  |
|-------------------|--------------------------------------------------------|
| Service type      | Web Service                                            |
| Region            | Oregon (or closest to demo audience)                   |
| Branch            | `main`                                                 |
| Root Directory    | `backend`                                              |
| Runtime           | Python 3                                               |
| Build Command     | `pip install -r requirements.txt`                      |
| Start Command     | `uvicorn main:app --host 0.0.0.0 --port $PORT`         |
| Instance type     | Starter ($7/mo) or Free (cold-start ~30s on first hit) |

### Environment variables

Paste these into Render → Settings → Environment.
**Values are in your local `backend/.env` — do NOT paste them here.**

```
BRIGHT_DATA_API_TOKEN          (from local .env)
BRIGHT_DATA_SERP_ZONE          serp_api1
BRIGHT_DATA_UNLOCKER_ZONE      web_unlocker1
BRIGHT_DATA_SCRAPER_DATASET_ID (from local .env)
ANTHROPIC_API_KEY              (from local .env)
ANTHROPIC_MODEL                claude-haiku-4-5-20251001
ANTHROPIC_MAX_TOKENS           1200
MIMO_API_KEY                   (from local .env)
USE_MOCK                       false
FAST_DEMO                      true
AUTO_WARMUP                    true
PYTHON_VERSION                 3.11.9
```

Notes:
- `ANTHROPIC_MODEL` / `ANTHROPIC_MAX_TOKENS` lock the cascade to cost-safe
  Haiku 4.5. Do not bump to Sonnet during the hackathon.
- `AUTO_WARMUP=true` triggers pre-caching of the 6 hero companies right
  after boot. First demo click then returns in milliseconds.
- `FAST_DEMO=true` collapses the SSE timeline delays so the live pitch
  doesn't burn 5 seconds of theater.

### After deploy — smoke test the backend

Replace `<BACKEND>` with the Render URL.

```powershell
# 1. Health — must show mode=live, claude=configured, mimo=configured
curl https://<BACKEND>/health

# Expected:
# { "status": "ok", "mode": "live", "claude": "configured",
#   "mimo": "configured", "version": "0.4.0" }

# 2. Live analyze — Anthropic OR Ramp. Should return llm_provider="claude"
#    (or "mimo" on Claude failure) and mode in {"live","hybrid"}.
curl -X POST https://<BACKEND>/analyze `
  -H "Content-Type: application/json" `
  -d '{\"company\":\"Anthropic\"}'

# Look for these fields in the response JSON:
#   "mode": "live" | "hybrid"
#   "llm_provider": "claude" | "mimo"
#   "evidence_hash": "<16-hex>"
#   evidence[].mode = "live" on at least 3 rows
```

If `/health` returns `mode=mock`, the `BRIGHT_DATA_API_TOKEN` env var
isn't set. If `claude=mock`, the `ANTHROPIC_API_KEY` isn't set. Fix the
env, redeploy, retest.

---

## 2 · Vercel — Frontend (Next.js)

### Project settings

| Field             | Value                          |
|-------------------|--------------------------------|
| Framework Preset  | Next.js                        |
| Root Directory    | `frontend`                     |
| Build Command     | (leave default — `next build`) |
| Output Directory  | (leave default)                |
| Node Version      | 20.x                           |

### Environment variable

```
NEXT_PUBLIC_API_BASE   https://<BACKEND>     (your Render URL, no trailing slash)
```

Set scope to **Production, Preview, Development** so previews also hit
the live backend.

### After deploy — smoke test the frontend

1. Open `https://<VERCEL_URL>/` — cockpit should render with the dark
   Palantir-style UI.
2. Type **Anthropic** (or click the chip) → hit Analyze.
3. The Agent Timeline (right rail) should advance through all 7 steps.
4. When the result lands, verify:
   - Mode badge shows **live** (or hybrid)
   - Why-Now score ring renders a number > 0
   - Evidence Ledger lists at least 3 rows with `mode=live`
   - Action Pack has a non-placeholder cold email
   - "Copy GTM Brief" button works
5. Click **Compare** with another hero (e.g. Anthropic vs Affirm) →
   side-by-side delta loads.

---

## 3 · Common gotchas

| Symptom                                                | Cause / fix                                              |
|--------------------------------------------------------|----------------------------------------------------------|
| Frontend shows mock mode despite live backend          | `NEXT_PUBLIC_API_BASE` missing or has trailing slash     |
| `/health` shows `claude=mock`                          | `ANTHROPIC_API_KEY` not set or wrong scope on Render     |
| First request takes 30+ seconds                        | Render free tier cold-start. Upgrade to Starter for demo |
| Evidence rows all show `mode=mock` after deploy        | `USE_MOCK` env var not set to `false`                    |
| Pre-warmup never finishes                              | Check Render logs for `[warmup]` lines — Bright Data quota or zone name wrong |
| CORS error in browser console                          | Backend already sets `allow_origins=["*"]`; check that frontend URL hits the deployed backend, not localhost |
| 504 timeout on first `/analyze`                        | Render free tier spins down; AUTO_WARMUP should re-warm on boot |

---

## 4 · Demo-day checklist (T-minus 1 hour)

- [ ] `/health` returns `mode=live`, `claude=configured`, `mimo=configured`
- [ ] Pre-warm by hitting `/warmup` once: `curl -X POST https://<BACKEND>/warmup`
- [ ] First-load test for all 6 heroes (NVIDIA, Anthropic, Affirm, Walmart, Marriott, Amazon) — each should return in <500ms after warmup
- [ ] One full UI run: Anthropic → cockpit fills → Copy GTM Brief works → Compare view works
- [ ] Browser dev console: no red errors
- [ ] Demo browser tab pinned, network unthrottled
- [ ] Backup: have the local `npm run dev` + `uvicorn` stack ready as fallback if cloud goes sideways

---

## 5 · Rolling back

If a Render or Vercel deploy goes bad:

- **Render**: Settings → Deploys → click the previous good deploy → "Rollback to this deploy"
- **Vercel**: Project → Deployments → previous deploy → "Promote to Production"

Both are one-click and ~10 seconds. Do this before debugging if the demo
is in <10 minutes.
