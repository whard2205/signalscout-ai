# CLAUDE.md — SignalScout AI

Project guide for Claude Code sessions. Read this first.

---

## What this project is

**SignalScout AI** — a "Why-Now Deal Intelligence Agent" built for the **Bright Data Web Data UNLOCKED Hackathon** (May 25–31, 2026, SF + online).

It answers one question for sales/GTM teams: *"Why should we contact this company right now?"*

User types a company name → backend pulls live web signals via Bright Data → Claude synthesizes an evidence-first intelligence report.

**Optimization target:** winning a 3-minute live demo. Demo wow + judge clarity > technical depth.

---

## Hard rules — non-negotiable

### Build priorities (in order)
1. Demo wow factor
2. UI polish
3. Stable workflow
4. Bright Data integration visibility
5. Enterprise narrative

### Do NOT build any of these
- Auth, login, OAuth
- Multi-tenant / orgs / CRM integration
- Vector DB / RAG layer
- Fine-tuning
- Multi-agent orchestration framework
- Microservices
- A chatbot (this is an **intelligence cockpit**, not a chat UI)

### Always
- **Demo-ready over technically perfect** — when in doubt, ship the demo path
- **Frontend polish > backend depth** — judges see the UI, not the code
- **Mock mode must always work** — if any live call fails, the cockpit must still render
- **Evidence-first** — every claim in the report ties to an evidence ID with source + Bright Data tool + confidence
- **No-BS AI** — if data is missing, output "Unknown" / "Insufficient evidence". Never hallucinate.
- **Explainable scores** — numeric scores are computed deterministically in `scoring.py`, NOT by the LLM

---

## Architecture

```
SignalScout-AI/
├── backend/                 FastAPI · Python 3.11+
│   ├── main.py              Entry point: uvicorn main:app --reload --port 8000
│   ├── requirements.txt
│   ├── .env.example         Copy to .env
│   └── app/
│       ├── api/routes.py    /health, /analyze, /analyze/stream (SSE)
│       ├── models/schemas.py  Pydantic models (single source of truth)
│       └── services/
│           ├── bright_data.py     SERP / Unlocker / Scraper wrapper · falls back to mock
│           ├── claude_service.py  Claude synthesis · returns None if not configured
│           ├── scoring.py         Deterministic score engine
│           └── mock_data.py       Seeded mock data — same input = same output
│
└── frontend/                Next.js 14 (app router) · Tailwind · TypeScript
    ├── app/page.tsx         Renders <Cockpit />
    ├── components/
    │   ├── Cockpit.tsx              Top-level layout + SSE wiring
    │   ├── AgentTimeline.tsx        Live pipeline (right rail)
    │   ├── WhyNowScore.tsx          Main score ring + 3 mini-scores
    │   ├── SignalGrid.tsx           8 signal kinds with icons
    │   ├── EvidenceLedger.tsx       Source-of-truth table
    │   ├── ActionPack.tsx           Cold email + LinkedIn + discovery
    │   ├── CompetitorTable.tsx
    │   ├── JudgeMode.tsx            Bright Data infrastructure panel
    │   └── ui/primitives.tsx        Card, Button, Badge, StatDot
    └── lib/
        ├── api.ts           analyzeOnce + analyzeStream (EventSource)
        ├── types.ts         Mirrors backend schemas.py
        └── utils.ts         cn(), formatTimeAgo()
```

### Data flow

```
User input → POST /analyze (or GET /analyze/stream)
  → build_mock_response(company)       # deterministic baseline
  → compute_scores(signals, evidence)  # deterministic numbers
  → synthesize(...)                    # optional Claude overlay
  → AnalyzeResponse                    # one JSON contract
```

Frontend mirrors `AnalyzeResponse` in `lib/types.ts`. If you change a backend schema field, update `types.ts` in the same commit.

### Mode states

`mode` on the response is one of:
- `"mock"` — no Bright Data token, no Claude key (default, demo-safe)
- `"hybrid"` — Claude overlay succeeded but Bright Data is still mocked
- `"live"` — Bright Data calls returned `status: ok`

The cockpit displays the mode as a badge. **Don't hide mock mode** — it's part of the safety story.

---

## Bright Data integration

Tools we use (must remain visible to judges):
- **SERP API** — live news + funding signals
- **Web Scraper API** — structured LinkedIn jobs, G2 reviews
- **Web Unlocker** — JS-rendered enterprise blogs
- **MCP Server** — orchestration narrative

`bright_data.py` always returns `(data, latency_ms, status)`. Errors are swallowed and surface via `status: "error"` so the demo can't crash. Don't add `raise` statements there.

API tokens live in `.env`. Never commit them. The `.env.example` is the contract.

---

## UI direction

Visual reference: **Palantir + Perplexity + Linear**.
- Dark enterprise SaaS palette (see `tailwind.config.ts`)
- Subtle grid backgrounds, conic-gradient score rings, soft glows
- No emojis in UI (chips, badges, icons only via `lucide-react`)
- All interactive elements use the same `Button`, `Badge`, `Card` primitives in `components/ui/primitives.tsx`

### Component rules

- Always extend `primitives.tsx` rather than building one-off styles
- Lucide icons only. No SVG inline.
- Animations: `animate-fade-up` and `animate-pulse-dot` are defined in tailwind config — reuse, don't add new ones
- No client-side data libraries (no SWR, no React Query, no Zustand). State is local. Streaming uses native `EventSource`.

---

## Streaming pipeline

`/analyze/stream` emits SSE events:
- `start` → cockpit shows "Live" indicator
- `step` → mark current step done, advance next to running
- `result` → renders the report
- `end` → close stream, set running=false

`TIMELINE_STEPS` in `backend/app/api/routes.py` and `PIPELINE` in `Cockpit.tsx` are kept in sync **by key**. If you add a step, add it in both places with the same `key`.

For demos, set `FAST_DEMO=true` in backend `.env` to shrink delays.

---

## Adding features — decision tree

Before adding anything, ask:
1. Does this make the 3-minute demo more compelling?
2. Can it be visually shown on a single screen?
3. Will it still work in mock mode if all APIs fail?
4. Can I ship it in under 4 hours?

If any answer is **no**, don't build it during the hackathon.

---

## Common tasks

### Add a new signal kind
1. Add the literal to `SignalCard.kind` in `backend/app/models/schemas.py`
2. Add the same in `SignalKind` in `frontend/lib/types.ts`
3. Add the icon mapping in `frontend/components/SignalGrid.tsx`
4. Add a row in `SIGNAL_WEIGHTS` in `backend/app/services/scoring.py`
5. Update mock generator in `mock_data.py` if you want it to show by default

### Wire a real Bright Data call
1. Set `USE_MOCK=false` and `BRIGHT_DATA_API_TOKEN=...` in `.env`
2. Add the call inside the relevant helper in `bright_data.py`
3. Convert raw response → `Evidence` rows in `routes.py`
4. **Keep the mock fallback path.** Live response shape may vary; don't crash on missing keys.

### Wire real Claude synthesis
- Already wired in `claude_service.py`. Set `ANTHROPIC_API_KEY=sk-ant-...` in `.env`.
- Default model: `claude-haiku-4-5-20251001` with `ANTHROPIC_MAX_TOKENS=1200` for lower demo cost/latency.
- Override with `ANTHROPIC_MODEL=...` only if quality is more important than cost.
- Prompt enforces the No-BS rules. Don't relax them — that's our differentiation.

---

## Anti-patterns to reject

- **"Let's also add X feature"** — say no unless it strengthens the 3-minute pitch
- **"Let's make it generic / framework-agnostic"** — this is a 6-day demo, not a library
- **"Let's switch to a database"** — SQLite if needed, otherwise in-memory. No Postgres.
- **"Let's add tests for everything"** — write tests only for `scoring.py` (the deterministic engine). Skip the rest.
- **"Let's refactor the routes file"** — it's <200 lines. Leave it.
- **"Let me add error toasts"** — handled via `mode` badge + console. Don't reinvent.

---

## Demo-day discipline

When the user is preparing for the demo:
1. **Don't suggest big refactors.** Suggest polish only.
2. **Pre-cache hero companies** (Ramp, Snowflake, Vercel, Linear, Notion) so they never hit a slow path.
3. **Verify mock mode works with backend offline** — frontend must still render an empty state cleanly.
4. **Suggest a rehearsal**, not new code.

---

## Reference

- Hackathon page: <https://brightdata.com> (Web Data UNLOCKED, May 25–31, 2026)
- Bright Data docs: <https://docs.brightdata.com>
- Anthropic SDK: `anthropic` Python package, default model `claude-haiku-4-5-20251001`
- `PLAN.md` in repo root has the day-by-day execution plan
- `README.md` has the quickstart + 3-minute demo script
