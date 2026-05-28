# SignalScout AI — 6-Day Hackathon Plan

**Hackathon:** Bright Data Web Data UNLOCKED · May 25–31, 2026
**Demo day:** May 31, 2026 (San Francisco + Online)
**Today:** May 18, 2026 — **7 days to kickoff**

---

## North Star

> Win a 3-minute live demo on stage. Optimize for **demo wow + judge clarity**, not technical depth.

---

## Track strategy

- **Primary:** Track 1 — GTM Intelligence (highest judge resonance, most data publicly available)
- **Secondary cross-track signal:** Track 2 (Finance) via hiring trends + funding signals — gets you bonus points

---

## Day-by-day

### Day 0 — Today → May 24 (pre-hackathon)
Setup only. Don't ship product yet (against rules).
- [x] Repo scaffolded (this commit)
- [ ] Run backend locally, confirm `/analyze` returns valid JSON in mock mode
- [ ] Run frontend locally, confirm cockpit renders + streams timeline
- [ ] Get Bright Data API token (request on Day 1 of hackathon)
- [ ] Get Anthropic API key (already have? otherwise free trial)
- [ ] Practice the 3-minute pitch on whiteboard 3x

### Day 1 — May 25 (kickoff, $250 credits unlock)
- [ ] Wire live SERP API call for `news` evidence
- [ ] Wire live Web Unlocker for one target company blog
- [ ] Verify health endpoint reports `mode: live`

### Day 2 — May 26
- [ ] Wire LinkedIn jobs via Web Scraper API dataset
- [ ] Real Claude synthesis end-to-end with one test company
- [ ] Tune timeline delays to feel smooth (target full run ~6–8s)

### Day 3 — May 27
- [ ] Polish UI: hover states, copy buttons, micro-animations
- [ ] Add 3 demo-target companies that always work flawlessly (pre-cached)
- [ ] Record 60-second teaser video for socials

### Day 4 — May 28
- [ ] End-to-end dry run with the actual pitch
- [ ] Add a "Demo mode" toggle that bypasses live calls (resilience)
- [ ] Polish judge-mode panel — make Bright Data branding obvious

### Day 5 — May 29
- [ ] Bug bash. Fix one thing only if it breaks the demo.
- [ ] Final pitch rehearsal x 3
- [ ] Push to Vercel + Render/Fly for live URL

### Day 6 — May 30 (onsite build day)
- [ ] Final polish onsite. Network. Talk to Bright Data engineers.
- [ ] Get someone outside the team to do the demo cold — no notes — find rough edges
- [ ] Sleep early

### Day 7 — May 31 (DEMO DAY)
- [ ] Test laptop on venue wifi early
- [ ] Have **offline-cached demo run** ready in case wifi dies
- [ ] Deliver the 3-minute pitch. Eye contact. Smile.

---

## What we will NOT build

If you find yourself building any of these, STOP:

- Auth, login, OAuth
- Multi-tenant / orgs
- Vector DB / RAG layer
- Fine-tuning
- Multi-agent orchestration framework
- Microservices
- A chatbot

Reason: 6 days. One killer workflow > five half-baked features.

---

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Bright Data API rate-limits during demo | Pre-cache 3 hero companies; fall back to mock on error |
| Wifi dies on stage | Mock mode is the default — demo never breaks |
| Claude latency makes demo feel slow | `FAST_DEMO=true` env shortens timeline steps |
| Judges miss the Bright Data angle | Judge Mode panel is permanent on the page |
| Hallucinated outputs embarrass us live | No-BS prompt + deterministic scoring + evidence ledger |

---

## Win conditions

1. Judges remember **one** phrase: *"Why-Now Deal Intelligence."*
2. Judges see Bright Data tools used **visibly** on screen.
3. Demo doesn't crash. Mock mode = insurance.
4. Pitch ends with a sales rep's voice, not an engineer's voice.
