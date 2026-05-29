# SignalScout AI — Demo Kit

Two artifacts for May 31 demo day:
1. **60-second teaser script** — record this for backup + social
2. **3-minute live pitch rehearsal checklist** — for stage

Both anchor on the same single phrase the judges should remember:
**"Why-Now Deal Intelligence — evidence-first, no hallucinated scores."**

---

## P3 — 60-Second Teaser Video Script

> Use this if you screen-record SignalScout on a hero company (e.g. Ramp). Camera
> on your face is optional; the screen recording is the star. Speak conversationally,
> not robotic.

### Setup before recording
- Run `curl -X POST http://localhost:8000/warmup` so Ramp/Snowflake/Vercel are cached
- Open `localhost:3000` in clean tab, full-screen
- Have terminal *closed* — clean visual
- Pick **Ramp** as the demo company

### Script (read out loud, 60 seconds)

**[0:00–0:08] Hook — face on camera or voiceover**
> "Sales teams spend 30% of their week figuring out *why* to contact a company *right now*. We automated that."

**[0:08–0:15] Cut to cockpit screen, type "Ramp"**
> "I type any company name. SignalScout AI pulls live web data through Bright Data —"

**[0:15–0:25] Timeline streams on the right rail**
> "— SERP API for news and competitors, Web Unlocker bypasses paywalls to read the full article — three Bright Data tools chained in one agent."

**[0:25–0:35] Why-Now score ring appears**
> "And here's the kicker — this score is *deterministic*. Computed in code, not hallucinated by an LLM. Every claim links to evidence with a source URL."

**[0:35–0:48] Scroll to Evidence Ledger + Action Pack**
> "Sales rep gets a cold email referencing the actual $500 million funding round Ramp just closed — pulled live from PR Newswire, ten seconds ago."

**[0:48–0:58] Cut back to face / cockpit overview**
> "That's SignalScout AI. Why-Now Deal Intelligence. Built on Bright Data for the Web Data UNLOCKED hackathon."

**[0:58–1:00] Logo + URL freeze frame**
> *(silence, frame holds 2 seconds)*

### Recording tools
- **OBS Studio** (free) → record screen + webcam
- **Loom** (free tier, easier) → one-click record, auto-trim
- **CapCut** (free, mobile + desktop) → cut, add captions

### Distribution
- Post to LinkedIn day before demo with caption: *"Demoing this at Bright Data Web Data UNLOCKED Saturday."*
- Twitter/X: same clip, tag @bright_data
- Use as fallback if stage wifi dies

---

## P4 — 3-Minute Live Pitch Rehearsal Checklist

> Target: deliver this 5 times before May 31. Time yourself each run. If you
> exceed 3:15, cut content.

### Pre-flight (5 min before going on stage)

- [ ] Plug into venue wifi, run `curl http://localhost:8000/health` — confirm `mode: live`
- [ ] Run `curl -X POST http://localhost:8000/warmup` — pre-cache 5 hero companies
- [ ] Open cockpit at `localhost:3000` in a clean browser tab, full-screen, zoom 110%
- [ ] Close all other tabs, mute notifications, plug in charger
- [ ] Have **Snowflake** ready to type (Ramp is your video hero — diversify)
- [ ] Take one deep breath. Smile.

### The pitch (3:00 total)

| Time | What you say | What you do on screen |
|---|---|---|
| **0:00–0:15** | "Sales teams waste 30% of their week answering one question: *why should we contact this company right now?* We built an AI agent that answers it in under 10 seconds, using only live web data." | Stand still. Eye contact with judges. |
| **0:15–0:30** | "I type any company. Watch what happens." | Click "Snowflake" chip. Timeline starts streaming. |
| **0:30–1:00** | "SignalScout fires three Bright Data tools concurrently — SERP API pulls news and funding signals, plus competitor alternatives. Web Unlocker bypasses paywalls to read full articles. All three live, all under 8 seconds." | Point to the agent timeline on the right as steps complete. |
| **1:00–1:20** | "Now the most important part — this Why-Now score? **Deterministic.** Computed in code. The LLM never picks a number. Every component is auditable." | Hover over Why-Now Score ring. Open the breakdown section. |
| **1:20–1:50** | "Every claim has a source." (click an evidence row) "TechCrunch — funding round. PR Newswire — full text via Web Unlocker. No hallucinations, no made-up metrics. This is *evidence-first AI*." | Scroll to Evidence Ledger. Click 1-2 source URLs. |
| **1:50–2:15** | "And here's what the sales rep actually gets — a cold email that references the real funding round, the real competitor pricing pressure, the real hiring signal. Ready to paste into Outreach." | Scroll to Action Pack. Hover Copy button. |
| **2:15–2:40** | "Behind it all — three live Bright Data tools, two more wired and ready. Five surfaces, one agent." | Scroll to Judge Mode panel. Point to each tool. |
| **2:40–3:00** | "SignalScout AI. Why-Now Deal Intelligence. Built for Bright Data Web Data UNLOCKED. Thank you." | Stand still. Eye contact. Smile. Wait. |

### Things to avoid

❌ "Um... so basically..."
❌ Long technical explanations of FastAPI / Next.js / async streaming
❌ Apologizing for anything ("sorry, let me wait for it to load")
❌ Reading from notes
❌ Touching laptop trackpad unnecessarily — pre-cache means demo is instant

### Things to do

✅ One key phrase repeated: **"Why-Now Deal Intelligence"**
✅ "Three live tools" — say this number, judges love specifics
✅ "Deterministic, not hallucinated" — twice
✅ Eye contact, not screen-staring
✅ Pause for laughs / nods — let the demo breathe

### Failure recovery — if something breaks mid-pitch

| Issue | Move |
|---|---|
| Wifi dies | "Even when the live calls fail, the cockpit gracefully degrades to demo mode — production-grade resilience. Let me show you the mock layer." (continue with mock, never apologize) |
| Cockpit doesn't load | Switch to the 60-second teaser video on your phone |
| Bright Data rate-limits | Same as wifi dies — fall back narrative |
| LLM call times out | "Notice the cockpit returned — that's because all scores are deterministic, not LLM-generated. The synthesis layer is optional." (refresh and continue) |
| Judge asks technical question | Answer in <30 sec, redirect to the cockpit visual |

### Mental checklist after each rehearsal

- [ ] Did I finish under 3:15?
- [ ] Did I say "Why-Now Deal Intelligence" out loud?
- [ ] Did I say "deterministic" out loud?
- [ ] Did I make eye contact at 0:00 and 3:00?
- [ ] Was there a single "um" longer than 1 second?
- [ ] Did the demo feel rushed or smooth?

After 5 runs, you'll have muscle memory. **That's when you win.**

---

## Day-of cheat card (print this, fold in pocket)

```
HOOK    → 30% of sales week wasted on "why now"
ACT 1   → type Snowflake, 3 Bright Data tools fire
ACT 2   → Why-Now score = DETERMINISTIC
ACT 3   → Evidence with real source URLs
ACT 4   → Action Pack = ready-to-paste cold email
CLOSE   → "Why-Now Deal Intelligence" — 3 tools live, 2 wired

If broken → "graceful degradation, production-grade resilience"
```
