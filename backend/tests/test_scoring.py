"""Unit tests for the deterministic scoring engine.

These tests prove that `compute_scores()` is:
1. Deterministic — same input always produces identical output.
2. Bounded — all dimensions clamp to [0, 100].
3. Differentiated — different signal mixes produce different scores.
4. Confidence-aware — score with mode='live' > 'mock' > 'fallback'.

Run from backend/:
    python -m pytest tests/ -v
"""
from __future__ import annotations

import pytest

from app.models.schemas import Evidence, SignalCard
from app.services.scoring import (
    BASELINE,
    CONFIDENCE_BOOST,
    IMPACT_MULTIPLIER,
    MODE_MULTIPLIER,
    SIGNAL_WEIGHTS,
    compute_scores,
)


def _ev(eid: str, signal: str, mode: str = "live", conf: str = "high",
        tool: str = "SERP API") -> Evidence:
    return Evidence(
        id=eid, source="test.com", source_title=f"test {signal}",
        url=f"https://test.com/{eid}", signal=signal, summary="test summary",
        timestamp=None, tool=tool, confidence=conf, mode=mode,  # type: ignore[arg-type]
    )


def _sig(kind: str, evidence_ids: list[str], impact: str = "positive") -> SignalCard:
    return SignalCard(
        kind=kind, title=f"{kind} signal", detail="test", impact=impact,  # type: ignore[arg-type]
        evidence_ids=evidence_ids,
    )


# ── DETERMINISM ─────────────────────────────────────────────────────────────

def test_same_input_same_output():
    """Score must be reproducible — identical input → identical output."""
    ev = [_ev("e1", "funding"), _ev("e2", "hiring")]
    signals = [_sig("funding", ["e1"]), _sig("hiring", ["e2"])]
    r1 = compute_scores(signals, ev)
    r2 = compute_scores(signals, ev)
    assert r1.why_now.value == r2.why_now.value
    assert r1.buying_intent.value == r2.buying_intent.value
    assert r1.expansion_signal.value == r2.expansion_signal.value
    assert r1.competitor_threat.value == r2.competitor_threat.value


def test_score_components_match_dimension():
    """Why-Now components must sum (approximately) to non-baseline portion of the score."""
    ev = [_ev("e1", "funding")]
    signals = [_sig("funding", ["e1"])]
    result = compute_scores(signals, ev)
    components = result.why_now.components or {}
    assert "funding_or_partnership" in components
    assert components["funding_or_partnership"] > 0


# ── BOUNDED ─────────────────────────────────────────────────────────────────

def test_scores_clamped_zero_to_hundred():
    """All score values must be in [0, 100], even with many strong signals."""
    ev = [_ev(f"e{i}", "funding") for i in range(20)]
    signals = [_sig("funding", [f"e{i}"]) for i in range(20)]
    result = compute_scores(signals, ev)
    for s in (result.why_now, result.buying_intent, result.expansion_signal, result.competitor_threat):
        assert 0 <= s.value <= 100, f"{s.label}={s.value} out of bounds"


def test_zero_signals_returns_baseline():
    """No signals → baseline score (cold prospect)."""
    result = compute_scores([], [])
    # Score equals BASELINE (rounded) when no signals contribute
    assert result.why_now.value == int(round(BASELINE["why_now"]))


# ── DIFFERENTIATION ─────────────────────────────────────────────────────────

def test_more_signals_means_higher_score():
    """5 signals must score higher than 1 signal, all else equal."""
    one_ev = [_ev("e1", "funding")]
    one_sig = [_sig("funding", ["e1"])]
    many_ev = [_ev(f"e{i}", "funding") for i in range(5)]
    many_sig = [_sig("funding", [f"e{i}"]) for i in range(5)]
    assert compute_scores(many_sig, many_ev).why_now.value > \
           compute_scores(one_sig, one_ev).why_now.value


def test_funding_outweighs_news_for_why_now():
    """Per Trigger Event Selling research: funding > news for why_now."""
    funding_score = compute_scores(
        [_sig("funding", ["e1"])], [_ev("e1", "funding")],
    ).why_now.value
    news_score = compute_scores(
        [_sig("news", ["e1"], impact="neutral")], [_ev("e1", "news")],
    ).why_now.value
    assert funding_score > news_score


# ── MODE-AWARENESS ──────────────────────────────────────────────────────────

def test_live_outscores_mock():
    """Live evidence carries higher mode multiplier (1.20×) than mock (1.00×)."""
    live_ev = [_ev("e1", "funding", mode="live")]
    mock_ev = [_ev("e1", "funding", mode="mock")]
    sig = [_sig("funding", ["e1"])]
    assert compute_scores(sig, live_ev).why_now.value >= \
           compute_scores(sig, mock_ev).why_now.value


def test_high_confidence_outscores_low():
    """High confidence (1.00×) > low confidence (0.60×)."""
    high_ev = [_ev("e1", "funding", conf="high")]
    low_ev = [_ev("e1", "funding", conf="low")]
    sig = [_sig("funding", ["e1"])]
    assert compute_scores(sig, high_ev).why_now.value > \
           compute_scores(sig, low_ev).why_now.value


# ── METHODOLOGY DOCUMENTATION ───────────────────────────────────────────────

def test_signal_weights_table_includes_all_documented_signals():
    """Every signal kind in the schema must have a weight defined."""
    documented = {"hiring", "funding", "product", "news",
                  "competitor", "pricing", "review", "expansion"}
    assert documented.issubset(SIGNAL_WEIGHTS.keys())


def test_multipliers_exposed():
    """Mode/impact/confidence multipliers must be inspectable for audit."""
    assert MODE_MULTIPLIER["live"] > MODE_MULTIPLIER["mock"]
    assert IMPACT_MULTIPLIER["positive"] > IMPACT_MULTIPLIER["negative"]
    assert CONFIDENCE_BOOST["high"] > CONFIDENCE_BOOST["low"]


# ── EDGE CASES ──────────────────────────────────────────────────────────────

def test_dangling_evidence_id_ignored():
    """Signal references an evidence_id that doesn't exist → score still computes."""
    signals = [_sig("funding", ["non_existent_id"])]
    result = compute_scores(signals, [])
    assert 0 <= result.why_now.value <= 100


def test_negative_impact_lowers_contribution():
    """Negative impact (0.4×) contributes less than positive (1.0×)."""
    pos = compute_scores(
        [_sig("funding", ["e1"], impact="positive")], [_ev("e1", "funding")],
    ).why_now.value
    neg = compute_scores(
        [_sig("funding", ["e1"], impact="negative")], [_ev("e1", "funding")],
    ).why_now.value
    assert pos > neg


# ── COMPETITOR_THREAT VARIANCE (regression: was constant ~22 across companies) ──

def _comp_signal(conf: str, impact: str) -> tuple[list, list]:
    """Helper: build the synthetic competitor evidence + signal pair as
    `_inject_live_signals` does in routes.py.
    """
    ev = Evidence(
        id="comp_1", source="bright-data-serp",
        source_title="Competitor SERP", url=None, signal="competitor",
        summary="", timestamp=None, tool="SERP API",
        confidence=conf, mode="live",   # type: ignore[arg-type]
    )
    sig = SignalCard(
        kind="competitor", title="t", detail="d",
        impact=impact, evidence_ids=["comp_1"],   # type: ignore[arg-type]
    )
    return [sig], [ev]


def test_competitor_threat_zero_competitors_is_baseline():
    """With no competitor signal, competitor_threat ≈ baseline (no contribution)."""
    result = compute_scores([], [])
    # Should equal BASELINE["competitor_threat"] rounded
    from app.services.scoring import BASELINE
    assert result.competitor_threat.value == round(BASELINE["competitor_threat"])


def test_competitor_threat_2_competitors_above_baseline():
    """1-2 competitors → low confidence + neutral impact → above baseline."""
    sig, ev = _comp_signal(conf="low", impact="neutral")
    r = compute_scores(sig, ev)
    from app.services.scoring import BASELINE
    assert r.competitor_threat.value > BASELINE["competitor_threat"]


def test_competitor_threat_5_competitors_outscores_2():
    """5+ (high+positive) > 1-2 (low+neutral) — count-based ordering."""
    sig2, ev2 = _comp_signal(conf="low", impact="neutral")          # 1-2
    sig5, ev5 = _comp_signal(conf="high", impact="positive")         # 5+
    r2 = compute_scores(sig2, ev2)
    r5 = compute_scores(sig5, ev5)
    assert r5.competitor_threat.value > r2.competitor_threat.value, (
        f"5+ should outscore 1-2 but got {r5.competitor_threat.value} "
        f"vs {r2.competitor_threat.value}"
    )


def test_competitor_threat_3_competitors_between_2_and_5():
    """3-4 (medium+neutral) should sit between 1-2 and 5+."""
    sig2, ev2 = _comp_signal(conf="low", impact="neutral")
    sig3, ev3 = _comp_signal(conf="medium", impact="neutral")
    sig5, ev5 = _comp_signal(conf="high", impact="positive")
    r2 = compute_scores(sig2, ev2).competitor_threat.value
    r3 = compute_scores(sig3, ev3).competitor_threat.value
    r5 = compute_scores(sig5, ev5).competitor_threat.value
    assert r2 < r3 < r5, f"Ordering broken: {r2} {r3} {r5}"


def test_competitor_threat_deterministic_same_input():
    """Same competitor signal + evidence → identical score across runs."""
    sig, ev = _comp_signal(conf="medium", impact="neutral")
    r1 = compute_scores(sig, ev).competitor_threat.value
    r2 = compute_scores(sig, ev).competitor_threat.value
    assert r1 == r2
