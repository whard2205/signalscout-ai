# SignalScout AI — Scoring Methodology

This document explains how SignalScout AI computes its Why-Now / Buying Intent /
Expansion / Competitor Threat scores. Everything described here is reproducible by
reading [`backend/app/services/scoring.py`](backend/app/services/scoring.py) and
running [`backend/tests/test_scoring.py`](backend/tests/test_scoring.py).

> **No LLM is involved in numeric score computation.** The LLM (Claude / MiMo) only
> synthesizes the executive-summary paragraph and why-now reason sentence above the
> score ring. Every number you see in the cockpit is computed by deterministic code
> from signal weights derived from published B2B GTM research.

---

## 1. The Formula

```
score(dim) = BASELINE(dim) + Σ over signals s:
              100 × weight(s, dim) × impact(s) × confidence_boost(s) × mode_multiplier(s)
```

clamped to `[0, 100]`.

| Term | Where defined | Why |
|---|---|---|
| `BASELINE` | [scoring.py:64-69](backend/app/services/scoring.py) | Prior probability of buying-window match for an unknown company (~10-14). |
| `weight` | [scoring.py:43-52](backend/app/services/scoring.py) | Signal-kind × dimension matrix — derived from research below. |
| `impact` | [scoring.py:55](backend/app/services/scoring.py) | positive=1.0, neutral=0.5, negative=0.4. |
| `confidence_boost` | [scoring.py:56](backend/app/services/scoring.py) | high=1.0, medium=0.85, low=0.6 — penalizes weak evidence. |
| `mode_multiplier` | [scoring.py:54](backend/app/services/scoring.py) | live=1.20, mock=1.00, fallback=0.90 — rewards verified-live data. |

All multipliers are **exposed in [`scoring.py`](backend/app/services/scoring.py)** for sales-ops audit. No magic constants.

---

## 2. Why these weights?

Signal weights are a **research-informed, transparent scoring heuristic** —
not a calibrated prediction model. The ORDERING is informed by published
B2B trigger-event and intent-data frameworks; the exact numeric values are
starting points exposed for audit and tuning by sales-ops teams.

> We do not claim the weights are universal truth. We claim they are
> **auditable, defensible defaults** that any team can inspect and adjust
> against their own pipeline conversion data.

### 2.1 Trigger Event Selling — Craig Elias

- **Reference**: *Shift! Harness the Trigger Events That Turn Prospects into Customers* — Craig Elias.
  [Google Books](https://books.google.com/books?id=mqciU-CowAMC)
- **Framing**: Funding rounds and leadership change are treated as high-value timing
  triggers in this methodology.
- **Our application**: `funding` is the highest-weighted `why_now` signal in our table.

### 2.2 6sense Buying-Stage Documentation

- **Reference**: 6sense intent-data and buying-stage docs.
  [Predictive Buying Stages](https://support.6sense.com/docs/predictive-buying-stages)
- **Framing**: Documents how observed research/activity signals map accounts into
  buying-cycle stages.
- **Our application**: supports our general stage-based treatment of public signals;
  it does not calibrate any exact SignalScout weight.

### 2.3 Forrester / SiriusDecisions Demand Unit Waterfall

- **Reference**: Forrester B2B revenue framework (acquired SiriusDecisions in 2019).
  [Forrester investor materials](https://investor.forrester.com/node/14636/pdf)
- **Framing**: A B2B demand-unit / buyer-journey framework.
- **Our application**: supports the idea that account activity should be separated
  by journey stage; it does not provide exact weights for expansion or competitors.

### 2.4 Demandbase Intent-Data Overview

- **Reference**: Demandbase intent-data product documentation.
  [Demandbase Intent Data](https://www.demandbase.com/solutions/intent-data/)
- **Framing**: B2B intent-data vendor describing how content velocity and
  engagement signals indicate awareness-stage buyer activity.
- **Our application**: informs our placement of `news` (awareness) signals at
  the lower end of the `why_now` weight table.

### 2.5 Bombora Company Surge / Intent-Data Overview

- **Reference**: Bombora Company Surge intent-data overview.
  [Bombora Intent Data](https://bombora.com/company-surge/)
- **Framing**: B2B intent-data co-op describing account-level topic research and
  content-consumption surges.
- **Our application**: supports the idea of account-level signal surges. We do not
  import or replicate Bombora's proprietary scoring data.

> **Important framing**: we do NOT claim our exact weight values (0.22, 0.18, etc.)
> are derived from these sources or empirically calibrated against private vendor
> data. The ORDERING of signal types reflects these published frameworks. The
> NUMBERS are tunable defaults exposed in code for sales-ops audit.

---

## 3. Weight Table — full SIGNAL_WEIGHTS

| Signal | why_now | buying_intent | expansion_signal | competitor_threat | Primary citation |
|---|---|---|---|---|---|
| funding | 0.22 | 0.20 | 0.20 | — | Elias 2009 |
| hiring | 0.18 | 0.25 | 0.10 | — | GTM heuristic |
| product | 0.18 | — | 0.22 | — | 6sense / Demandbase |
| expansion | 0.10 | — | 0.22 | — | Forrester framing |
| news | 0.10 | — | 0.08 | — | Demandbase |
| competitor | 0.08 | — | — | 0.35 | Gartner CHAMP |
| pricing | 0.05 | — | — | 0.18 | Gartner CHAMP |
| review | — | 0.05 | — | 0.10 | G2/Capterra |

Source of truth: [`scoring.py`](backend/app/services/scoring.py#L43-L52).

---

## 4. Mode-Multiplier Rationale

| Mode | Multiplier | Justification |
|---|---|---|
| `live` | 1.20× | Real-time data from Bright Data — most trustworthy. |
| `mock` | 1.00× | Demo baseline — no penalty, no bonus. |
| `fallback` | 0.90× | Live attempt failed → reduced confidence. |

This is the **only place** mode affects scoring. It does not alter signal-kind
weights — those reflect domain research, not data freshness.

---

## 5. Reproducibility

Every `/analyze` response includes an `evidence_hash` field — the first 16 hex chars
of `SHA256(evidence IDs + scores)`. Two runs with the same input return the same hash.
This is the audit-grade proof that the pipeline is deterministic.

Run the unit tests yourself:

```bash
cd backend
python -m pytest tests/ -v
# expected: 12 passed in <1s
```

Tests verify:
1. Same input → same output (`test_same_input_same_output`)
2. Bounded `[0, 100]` even with extreme inputs (`test_scores_clamped_zero_to_hundred`)
3. More signals → higher score (`test_more_signals_means_higher_score`)
4. Funding > news for why_now (`test_funding_outweighs_news_for_why_now`)
5. Live > mock > fallback ordering (`test_live_outscores_mock`)
6. High > low confidence ordering (`test_high_confidence_outscores_low`)
7. ... and 6 more

---

## 6. What the LLM does (and doesn't do)

| Layer | Implementation | What it outputs |
|---|---|---|
| **Numeric scores** | `scoring.py` (Python, deterministic) | `why_now: 82`, `buying_intent: 69`, etc. |
| **Executive summary** | Claude / MiMo synthesis | 2-3 sentence paragraph |
| **Why-Now reason** | Claude / MiMo synthesis | 1 punchy sentence with concrete numbers |
| **Action Pack** (cold email, etc.) | LLM if it returns valid output, else `_live_action_pack()` deterministic fallback | 3 sales angles, cold email, LinkedIn msg, 3 discovery Qs |

The LLM is a **narrative layer** on top of deterministic scoring. It can fail entirely
(rate-limit, timeout) and the cockpit still renders complete numerical analysis with
deterministic action-pack fallback.

---

## 7. Tuning for Your Pipeline

These weights are starting points based on published research. Real sales ops should
tune them against historical conversion data:

```python
# In scoring.py
SIGNAL_WEIGHTS["funding"]["buying_intent"] = 0.30  # if your data shows
                                                    # funding events convert at 30%+
```

The whole point of exposing weights in code is so this is auditable and adjustable.
LLM-generated scores cannot be tuned because there's nothing to tune.

---

## References

These are the frameworks that **inform the ordering** of our signal weights.
We do not claim our exact numeric weights are derived from or empirically
calibrated against these sources — they are tunable defaults.

| Tag | Source |
|---|---|
| Elias | Elias, Craig. *Shift! Harness the Trigger Events That Turn Prospects into Customers*. [Google Books](https://books.google.com/books?id=mqciU-CowAMC) |
| 6sense | 6sense intent-data and buying-stage documentation. [support.6sense.com/docs/predictive-buying-stages](https://support.6sense.com/docs/predictive-buying-stages) |
| Forrester | Forrester / SiriusDecisions Demand Unit Waterfall. [Forrester investor materials](https://investor.forrester.com/node/14636/pdf) |
| Demandbase | Demandbase intent-data overview. [demandbase.com/solutions/intent-data](https://www.demandbase.com/solutions/intent-data/) |
| Bombora | Bombora Company Surge intent-data overview. [bombora.com/company-surge](https://bombora.com/company-surge/) |
