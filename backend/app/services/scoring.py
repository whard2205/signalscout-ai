"""Deterministic scoring engine.

Scores are computed from signal weights — never invented by the LLM.
Every numeric output traces to a specific evidence item and signal kind.
The `components` dict on the Why-Now score breaks down which signal
kinds contributed what, so judges can see exactly why the number is what it is.

──────────────────────────────────────────────────────────────────────────
SCORING APPROACH — research-informed, auditable, tunable
──────────────────────────────────────────────────────────────────────────

This is NOT a prediction model and NOT an LLM judgment. It is a
**transparent timing heuristic** for GTM intent:

  live evidence  →  typed signals  →  explicit weights  →  numeric score

The ORDERING of signal weights is informed by common B2B trigger-event
and intent-data frameworks (NOT empirically calibrated against private
conversion data — those numbers are not ours to claim):

  1. Trigger Event Selling (Craig Elias) — points to funding events
     and leadership change as high-value timing triggers.
       https://books.google.com/books?id=mqciU-CowAMC

  2. 6sense intent-data documentation — buying-stage signals include
     hiring surges, content consumption, and competitor evaluation.
       https://support.6sense.com/docs/predictive-buying-stages

  3. Forrester / SiriusDecisions Demand Unit Waterfall — B2B revenue
     buyer-journey framework distinguishing awareness vs late-funnel.
       https://investor.forrester.com/node/14636/pdf

The ordering — funding (0.22) > hiring/product (0.18) > expansion/news
(0.10) > competitor (0.08) — reflects these published frameworks. We do
NOT claim the exact numbers are universal truth. They are starting
points that sales-ops teams should tune against their own pipeline data.

What this DOES guarantee:
  - Same input → same score (deterministic, see tests/test_scoring.py)
  - Every weight is in code, inspectable, version-controlled
  - LLM never picks a number — synthesis is narrative only
  - Reproducibility hash on every response → verifiable across runs

Positioning: an **auditable, anti-hallucination scoring engine for GTM
timing**. Not a black-box prediction model.

──────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

from typing import Iterable

from app.models.schemas import Evidence, Score, Scores, SignalCard


# Weight table: signal kind -> score dimension -> raw weight (0..1).
# Ordering grounded in B2B intent frameworks — see module docstring above.
#
# Light cross-dimension weights on product/expansion → buying_intent so
# companies with product launches or expansion activity register some
# buying-intent lift even without an explicit hiring/funding event. Without
# these, buying_intent plateaus at ~42 (baseline 12 + hiring contribution
# ~30) for any company whose only positive signal is hiring.
SIGNAL_WEIGHTS: dict[str, dict[str, float]] = {
    "hiring":     {"why_now": 0.18, "buying_intent": 0.25, "expansion_signal": 0.10},
    "funding":    {"why_now": 0.22, "buying_intent": 0.20, "expansion_signal": 0.20},
    "product":    {"why_now": 0.18, "expansion_signal": 0.22, "buying_intent": 0.08},
    "news":       {"why_now": 0.10, "expansion_signal": 0.08},
    "competitor": {"competitor_threat": 0.35, "why_now": 0.08},
    "pricing":    {"competitor_threat": 0.18, "why_now": 0.05},
    "review":     {"competitor_threat": 0.10, "buying_intent": 0.05},
    "expansion":  {"expansion_signal": 0.22, "why_now": 0.10, "buying_intent": 0.06},
}

# Multipliers — also documented and audit-able.
MODE_MULTIPLIER: dict[str, float] = {"live": 1.20, "mock": 1.00, "fallback": 0.90}
IMPACT_MULTIPLIER: dict[str, float] = {"positive": 1.0, "neutral": 0.5, "negative": 0.4}
CONFIDENCE_BOOST: dict[str, float] = {"low": 0.6, "medium": 0.85, "high": 1.0}

# Baseline = "score before any signals" — represents the prior probability
# that a randomly-selected company is a buying-window match. Calibrated so
# zero-signal companies score ~10 (cold prospect) and signal-rich companies
# land in the 70-90 range. A perfect 100 should be rare, not default.
BASELINE: dict[str, float] = {
    "why_now": 10.0,
    "buying_intent": 12.0,
    "expansion_signal": 14.0,
    "competitor_threat": 12.0,
}

# Why-Now component names (for judge-visible breakdown)
WHY_NOW_COMPONENTS = [
    "hiring_signal",
    "news_momentum",
    "product_launch",
    "competitor_pressure",
    "review_pain",
    "funding_or_partnership",
]

KIND_TO_COMPONENT: dict[str, str] = {
    "hiring":     "hiring_signal",
    "news":       "news_momentum",
    "product":    "product_launch",
    "competitor": "competitor_pressure",
    "pricing":    "competitor_pressure",
    "review":     "review_pain",
    "funding":    "funding_or_partnership",
    "expansion":  "funding_or_partnership",
}


def _clamp(v: float) -> int:
    return max(0, min(100, int(round(v))))


def _avg_conf(evidence_ids: Iterable[str], by_id: dict[str, Evidence]) -> str:
    levels = [by_id[eid].confidence for eid in evidence_ids if eid in by_id]
    if not levels:
        return "low"
    order = {"low": 1, "medium": 2, "high": 3}
    avg = sum(order[l] for l in levels) / len(levels)
    return "high" if avg >= 2.5 else "medium" if avg >= 1.6 else "low"


def _evidence_mode(evidence_ids: Iterable[str], by_id: dict[str, Evidence]) -> str:
    modes = [by_id[eid].mode for eid in evidence_ids if eid in by_id]
    if "live" in modes:
        return "live"
    if "fallback" in modes:
        return "fallback"
    return "mock"


def compute_scores(signals: list[SignalCard], evidence: list[Evidence]) -> Scores:
    raw: dict[str, float] = dict(BASELINE)
    why_now_components: dict[str, float] = {c: 0.0 for c in WHY_NOW_COMPONENTS}

    rationale_bits: dict[str, list[str]] = {k: [] for k in BASELINE}
    conf_per_dim: dict[str, list[str]] = {k: [] for k in BASELINE}

    by_id = {e.id: e for e in evidence}

    for sig in signals:
        weights = SIGNAL_WEIGHTS.get(sig.kind, {})
        impact = IMPACT_MULTIPLIER[sig.impact]
        conf = _avg_conf(sig.evidence_ids, by_id)
        mode = _evidence_mode(sig.evidence_ids, by_id)
        boost = CONFIDENCE_BOOST[conf] * MODE_MULTIPLIER[mode]

        for dim, w in weights.items():
            delta = 100.0 * w * impact * boost
            raw[dim] += delta
            rationale_bits[dim].append(sig.title)
            conf_per_dim[dim].append(conf)

        # Track why-now component contribution
        component = KIND_TO_COMPONENT.get(sig.kind)
        if component and "why_now" in weights:
            why_now_components[component] += 100.0 * weights["why_now"] * impact * boost

    def _confidence(dim: str) -> str:
        levels = conf_per_dim[dim]
        if not levels:
            return "low"
        order = {"low": 1, "medium": 2, "high": 3}
        avg = sum(order[l] for l in levels) / len(levels)
        return "high" if avg >= 2.5 else "medium" if avg >= 1.6 else "low"

    def _rationale(dim: str) -> str:
        bits = rationale_bits[dim][:3]
        return "Driven by: " + ", ".join(bits) if bits else "No strong signal detected."

    # Clamp component values for display
    clamped_components = {k: _clamp(v) for k, v in why_now_components.items()}

    return Scores(
        why_now=Score(
            value=_clamp(raw["why_now"]),
            label="Why-Now",
            rationale=_rationale("why_now"),
            confidence=_confidence("why_now"),  # type: ignore[arg-type]
            components=clamped_components,
        ),
        buying_intent=Score(
            value=_clamp(raw["buying_intent"]),
            label="Buying Intent",
            rationale=_rationale("buying_intent"),
            confidence=_confidence("buying_intent"),  # type: ignore[arg-type]
        ),
        expansion_signal=Score(
            value=_clamp(raw["expansion_signal"]),
            label="Expansion",
            rationale=_rationale("expansion_signal"),
            confidence=_confidence("expansion_signal"),  # type: ignore[arg-type]
        ),
        competitor_threat=Score(
            value=_clamp(raw["competitor_threat"]),
            label="Competitor Threat",
            rationale=_rationale("competitor_threat"),
            confidence=_confidence("competitor_threat"),  # type: ignore[arg-type]
        ),
    )
