"""Data-quality regression tests.

These pin behavior for:
  - competitor name extraction (junk rejection, valid acceptance,
    empty-when-low-confidence threshold, never-self-as-competitor)
  - signal classification (earnings → news, investing-in → expansion,
    raised → funding)
  - source authority tier (subdomain heuristics, primary IR/press)
  - Web Unlocker partial-vs-full status
  - freshness-aware confidence decay
"""
from __future__ import annotations

import pytest

from app.services.bright_data import (
    _classify_source_tier,
    _detect_signal,
    _extract_competitors_from_snippet,
    _freshness_aware_confidence,
    _looks_like_competitor_name,
    _parse_competitor_serp_response,
)


# ── COMPETITOR PARSER ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("junk_name", [
    "Sellers Should Watch",
    "Top",
    "Best",
    "Brick",
    "Parallel",
    "HappyRobot",
    "Watch",
    "Companies",
    "Alternatives",
    "Competitors",
    "Read More",
    "Learn More",
    "Click Here",
    "United States",
    "North America",
    "This Year",
    "In 2025",
    "Guide",
    "Review",
    "Market",
])
def test_competitor_quality_gate_rejects_junk(junk_name: str) -> None:
    assert _looks_like_competitor_name(junk_name, "AnyCompany") is False, \
        f"Expected {junk_name!r} to be rejected as a competitor name"


@pytest.mark.parametrize("valid_name", [
    "Target",
    "Costco",
    "Costco Wholesale",
    "Brex",
    "Tipalti",
    "ChatGPT",
    "Microsoft Copilot",
    "Walmart",
    "AMD",      # 3-letter ALL-CAPS acronym
    "IHG",
    "IBM",
    "SAP",
])
def test_competitor_quality_gate_accepts_valid(valid_name: str) -> None:
    # Use an unrelated company so the self-rejection rule doesn't fire
    assert _looks_like_competitor_name(valid_name, "OtherCo") is True, \
        f"Expected {valid_name!r} to be accepted as a competitor name"


def test_competitor_quality_gate_rejects_company_itself() -> None:
    """Never include the analyzed company in its own competitor list."""
    assert _looks_like_competitor_name("Amazon", "Amazon") is False
    assert _looks_like_competitor_name("amazon", "Amazon") is False
    assert _looks_like_competitor_name("AMAZON INC", "Amazon") is False


# ── GEOGRAPHY / GENERIC NOUN REJECTION ───────────────────────────────────────

@pytest.mark.parametrize("geo_name", [
    # Continents / regions
    "Asia", "Europe", "Africa", "North America", "South America",
    "Middle East", "Southeast Asia", "APAC", "EMEA",
    # Countries (the ones that cause real SERP noise)
    "China", "India", "Indonesia", "Malaysia", "Singapore",
    "Japan", "Korea", "Vietnam", "Thailand", "Philippines",
    "Taiwan", "Hong Kong", "Mongolia",
    "Germany", "France", "Spain", "Italy",
    "Brazil", "Mexico", "Canada", "Australia",
    "Saudi Arabia", "Israel", "Turkey", "Russia",
    # Cities
    "Jakarta", "Mumbai", "Tokyo", "Shanghai", "Beijing",
    "Dubai", "London", "Paris", "New York", "Singapore",
    # Programming-language / island names mistaken for companies
    "Java", "Python", "Ruby", "Scala",
    # Misc geo
    "Global", "International",
])
def test_competitor_quality_gate_rejects_geography(geo_name: str) -> None:
    """Geography is never a competitor — countries, regions, cities, languages."""
    assert _looks_like_competitor_name(geo_name, "Pertamina") is False, \
        f"Expected {geo_name!r} to be rejected as geography"


@pytest.mark.parametrize("generic_noun", [
    # Industry / tech words
    "Cloud", "Data", "AI", "Search", "App", "Platform",
    "Network", "Wireless", "Telecom", "Telco",
    "Energy", "Oil", "Gas", "Power", "Utility",
    "Mining", "Steel", "Chemicals", "Pharma",
    "Finance", "Fintech", "Banking", "Insurance",
    "Media", "Streaming", "Gaming", "Sports",
    "Health", "Healthcare", "Education", "Travel",
    # Tech building blocks
    "Software", "Hardware", "Service", "System", "Solution",
    "Infrastructure", "Consulting",
])
def test_competitor_quality_gate_rejects_generic_single_nouns(
    generic_noun: str,
) -> None:
    """Standalone industry / tech / common nouns are not competitor names."""
    assert _looks_like_competitor_name(generic_noun, "OtherCo") is False, \
        f"Expected {generic_noun!r} to be rejected as a generic single-word noun"


def test_competitor_quality_gate_rejects_geo_plus_industry_combo() -> None:
    """Country + industry-noun fragments like 'China Energy' / 'Malaysia Telecom'
    are SEO listicle headers, not real B2B company names."""
    for fake in ["China Energy", "Malaysia Telecom", "Indonesia Oil",
                 "Asia Cloud", "India Software", "Singapore Bank"]:
        assert _looks_like_competitor_name(fake, "Pertamina") is False, \
            f"Expected {fake!r} to be rejected as geo+industry fragment"


def test_competitor_quality_gate_keeps_brand_with_industry_word() -> None:
    """A REAL brand name that happens to contain an industry word stays valid."""
    # "Snowflake" is a brand but contains nothing generic — keep
    assert _looks_like_competitor_name("Snowflake", "Databricks") is True
    # Multi-word brand: real brand + tech word should still pass
    # (only rejected when EVERY word is generic/geo)
    assert _looks_like_competitor_name("Brex Cash", "Ramp") is True


# ── CONFIDENCE-AWARE EXTRACTION ──────────────────────────────────────────────

def _wrap_bd(raw_body: dict) -> dict:
    """Bright Data wraps SERP JSON inside {body: <json-string>}."""
    import json as _json
    return {"body": _json.dumps(raw_body)}


def test_competitor_extraction_tags_explicit_as_strong() -> None:
    """Explicit 'competitors include X, Y, Z' snippet → threat='high'."""
    raw_body = {
        "organic": [
            {
                "link": "https://walmart-competitors.example.com/list",
                "title": "Top Walmart Competitors",
                "description": "Walmart competitors include Target, Costco, Kroger, Aldi.",
            },
        ],
    }
    out = _parse_competitor_serp_response(_wrap_bd(raw_body), "Walmart")
    assert len(out) >= 2, f"Expected ≥2 competitors, got {out}"
    # The explicit-snippet names must all be tagged high
    explicit_names = {"Target", "Costco", "Kroger", "Aldi"}
    high_named = {c["name"] for c in out if c["threat"] == "high"}
    assert explicit_names.issubset(high_named), \
        f"Explicit-snippet names should be threat=high. Got: {out}"


def test_competitor_extraction_tags_domain_fallback_as_weak() -> None:
    """Domain-only extractions (no explicit competitor-list snippet) →
    threat='low'. Need ≥3 clean domains to publish; weak-only with 1-2 → []."""
    raw_body = {
        "organic": [
            {"link": "https://brex.com/",     "title": "Brex Corporate Cards",
             "description": "Modern corporate card solution."},
            {"link": "https://ramp.com/",     "title": "Ramp Spend Management",
             "description": "Spend management platform."},
            {"link": "https://tipalti.com/",  "title": "Tipalti Payouts",
             "description": "Mass payments platform."},
        ],
    }
    out = _parse_competitor_serp_response(_wrap_bd(raw_body), "Mercury")
    assert len(out) >= 3, f"Expected ≥3 weak competitors, got {out}"
    assert all(c["threat"] == "low" for c in out), \
        f"Domain-fallback competitors should be threat=low: {out}"


def test_competitor_extraction_returns_empty_when_only_one_weak_match() -> None:
    """A single clean domain hit with no explicit competitor-list snippet
    is not enough — return [] to avoid faking competitor pressure."""
    raw_body = {
        "organic": [
            {"link": "https://brex.com/", "title": "Brex Corporate Cards",
             "description": "Modern corporate card solution."},
            # Everything else is a skipped aggregator
            {"link": "https://g2.com/walmart-alternatives",
             "title": "Walmart Alternatives",
             "description": "..."},
            {"link": "https://reddit.com/r/whatever",
             "title": "Some thread",
             "description": "..."},
        ],
    }
    out = _parse_competitor_serp_response(_wrap_bd(raw_body), "Mercury")
    assert out == [], f"Expected [] (single weak hit), got {out}"


def test_competitor_extraction_drops_geography_competitor() -> None:
    """If a snippet lists 'China, Malaysia, Java' as competitors, the
    quality gate rejects them — parser returns [] (no real competitor)."""
    raw_body = {
        "organic": [
            {
                "link": "https://example.com/pertamina-competitors",
                "title": "Top Pertamina Competitors",
                "description": "Pertamina competitors include China, Malaysia, Java.",
            },
        ],
    }
    out = _parse_competitor_serp_response(_wrap_bd(raw_body), "Pertamina")
    # All three are geography → all rejected → strong=0, weak=0 → []
    assert out == [], f"Expected [] (all junk geo), got {out}"


def test_bank_central_asia_serp_rejects_central_asia_region_noise() -> None:
    """BCA must not match generic Central Asia regional development news."""
    from app.services.bright_data import _parse_serp_response

    raw_body = {
        "organic": [
            {
                "link": "https://www.ebrd.com/news/central-asia-investment",
                "title": "EBRD invests almost US$ 2 billion in Central Asia and Mongolia",
                "description": "Central Asia infrastructure investment program expands.",
            },
            {
                "link": "https://www.bca.co.id/report.pdf",
                "title": "PT Bank Central Asia Tbk - 1Q26 Results",
                "description": "BCA reports quarterly performance.",
            },
        ],
    }
    out = _parse_serp_response(_wrap_bd(raw_body), "Bank Central Asia")
    assert len(out) == 1
    assert out[0]["source"] == "bca.co.id"
    assert "EBRD" not in out[0]["source_title"]


def test_telkomsel_competitors_reject_off_market_charter_noise() -> None:
    """Telkomsel competitor results must mention Telkomsel, not generic US telco lists."""
    raw_body = {
        "organic": [
            {
                "link": "https://example.com/charter",
                "title": "Charter Communications competitors",
                "description": "Charter competitors include Comcast, Verizon, AT&T.",
            },
            {
                "link": "https://example.com/telkomsel-competitors",
                "title": "Telkomsel competitors include Indosat, XL Axiata, Smartfren",
                "description": "Telkomsel competitors include Indosat, XL Axiata, Smartfren in Indonesia.",
            },
        ],
    }
    out = _parse_competitor_serp_response(_wrap_bd(raw_body), "Telkomsel")
    names = {row["name"] for row in out}
    assert {"Indosat", "XL Axiata", "Smartfren"}.issubset(names)
    assert "Charter Communications" not in names


# ── COMPETITOR_THREAT SCORING RESPECTS QUALITY ───────────────────────────────

def test_no_competitor_evidence_keeps_threat_at_baseline() -> None:
    """No competitor SignalCard → competitor_threat ≈ baseline only."""
    from app.services.scoring import BASELINE, compute_scores
    # Provide no competitor signal at all
    result = compute_scores([], [])
    assert result.competitor_threat.value == round(BASELINE["competitor_threat"])


def test_high_quality_competitor_set_outscores_low_quality() -> None:
    """A high-confidence competitor signal (3+ explicit) scores higher than
    a low-confidence one (only weak fallback). Deterministic."""
    from app.models.schemas import Evidence, SignalCard
    from app.services.scoring import compute_scores

    def _eval(conf: str, impact: str) -> int:
        ev = Evidence(
            id="comp_1", source="bright-data-serp", source_title="t",
            url=None, signal="competitor", summary="t",
            timestamp=None, tool="SERP API",
            confidence=conf, mode="live",  # type: ignore[arg-type]
        )
        sig = SignalCard(
            kind="competitor", title="t", detail="d",
            impact=impact, evidence_ids=["comp_1"],  # type: ignore[arg-type]
        )
        return compute_scores([sig], [ev]).competitor_threat.value

    high = _eval("high", "positive")
    low = _eval("low", "neutral")
    assert high > low, f"high={high} should outscore low={low}"


def test_extract_competitors_from_hostile_snippet() -> None:
    """Listicle-format snippet should yield clean names + drop 'Sellers Should Watch'."""
    snippet = (
        "Top 5 Amazon Competitors and Alternatives in 2026: "
        "Walmart, Target, Sellers Should Watch eBay, Etsy, Brick and mortar."
    )
    out = _extract_competitors_from_snippet(snippet, "Amazon", set())
    assert "Walmart" in out
    assert "Target" in out
    # All junk fragments rejected
    for junk in ("Sellers Should Watch", "Brick", "Top", "Companies"):
        assert junk not in out, f"{junk!r} leaked into output: {out}"


# ── COMPETITOR DENSITY SCALING (5 strong < 8 strong) ─────────────────────────

def _build_competitor_signals(n_strong: int) -> tuple[list, list]:
    """Return (signals, evidence) emulating what _inject_live_signals produces
    for `n_strong` competitors above the 3-threshold.

    Mirrors backend/app/api/routes.py:_inject_live_signals — primary
    competitor SignalCard plus secondary pricing SignalCards (one per extra
    strong competitor above 3, capped at 5; confidence decays after 2).
    """
    from app.models.schemas import Evidence, SignalCard

    ev: list = []
    sig: list = []
    # Primary competitor signal — high conf, positive, live
    ev.append(Evidence(
        id="comp_1", source="bright-data-serp", source_title="primary",
        url=None, signal="competitor", summary="t", timestamp=None,
        tool="SERP API", confidence="high", mode="live",  # type: ignore[arg-type]
    ))
    sig.append(SignalCard(
        kind="competitor", title="primary", detail="d",
        impact="positive", evidence_ids=["comp_1"],  # type: ignore[arg-type]
    ))
    extras = max(0, n_strong - 3)
    capped = min(extras, 5)
    for i in range(capped):
        extra_conf = "medium" if i < 2 else "low"
        eid = f"comp_density_{i + 1}"
        ev.append(Evidence(
            id=eid, source="bright-data-serp", source_title="extra",
            url=None, signal="pricing", summary="t", timestamp=None,
            tool="SERP API", confidence=extra_conf, mode="live",  # type: ignore[arg-type]
        ))
        sig.append(SignalCard(
            kind="pricing", title="extra", detail="d",
            impact="neutral", evidence_ids=[eid],  # type: ignore[arg-type]
        ))
    return sig, ev


def test_competitor_threat_8_strong_outscores_5_strong() -> None:
    """Regression: 8 strong competitors must produce a higher
    competitor_threat than 5 strong competitors. Pins the count-based
    scaling fix so we never silently revert to the 54-plateau bug."""
    from app.services.scoring import compute_scores

    sig5, ev5 = _build_competitor_signals(5)
    sig8, ev8 = _build_competitor_signals(8)
    score5 = compute_scores(sig5, ev5).competitor_threat.value
    score8 = compute_scores(sig8, ev8).competitor_threat.value
    assert score8 > score5, (
        f"8-strong ({score8}) must outscore 5-strong ({score5}). "
        "If this fails, the competitor density scaling regressed to a plateau."
    )


def test_competitor_threat_3_strong_lowest_in_strong_set() -> None:
    """Niche / specialist companies (exactly 3 strong competitors, no extras)
    must score LOWER than companies with 5 or 8 strong competitors."""
    from app.services.scoring import compute_scores

    sig3, ev3 = _build_competitor_signals(3)
    sig5, ev5 = _build_competitor_signals(5)
    score3 = compute_scores(sig3, ev3).competitor_threat.value
    score5 = compute_scores(sig5, ev5).competitor_threat.value
    assert score3 < score5, (
        f"3-strong ({score3}) should score lower than 5-strong ({score5}). "
        "Niche markets must register as less competitively dense."
    )


def test_competitor_threat_monotonic_in_strong_count() -> None:
    """Scores must be monotonically non-decreasing as strong-count rises
    from 3 → 4 → 5 → 6 → 7 → 8. (Equal is OK if the density cap binds;
    strictly decreasing would indicate a bug.)"""
    from app.services.scoring import compute_scores

    scores = []
    for n in range(3, 9):  # 3..8 inclusive
        sig, ev = _build_competitor_signals(n)
        scores.append(compute_scores(sig, ev).competitor_threat.value)
    for i in range(1, len(scores)):
        assert scores[i] >= scores[i - 1], (
            f"Non-monotonic at n={i + 3}: {scores}. "
            "competitor_threat must never drop as more competitors appear."
        )


def test_extract_competitors_returns_empty_when_no_intro() -> None:
    """Snippet without 'competitors are/include' intro returns empty list."""
    snippet = "Amazon reported strong Q1 results with revenue up 12%."
    out = _extract_competitors_from_snippet(snippet, "Amazon", set())
    assert out == []


def test_parse_competitor_serp_response_empty_when_low_confidence() -> None:
    """If we can only find 0 or 1 credible competitor, return [] not noise."""
    raw_body = {
        "organic": [
            # Only one organic result that's also from a skipped domain
            {"link": "https://reddit.com/r/whatever",
             "title": "Discussion: Should Amazon worry about competition?",
             "description": "Some users mention Sellers Should Watch as one to keep an eye on."},
        ],
    }
    # Wrap as Bright Data does
    out = _parse_competitor_serp_response({"body": __import__("json").dumps(raw_body)}, "Amazon")
    # Either empty OR at least 2 clean items — never just one junk row
    assert out == [] or len(out) >= 2


# ── SIGNAL CLASSIFICATION ────────────────────────────────────────────────────

@pytest.mark.parametrize("text, expected", [
    # Earnings/financial → news (NOT product)
    ("Amazon Q1 2026 results released today",        "news"),
    ("Net sales increased 12% year-over-year",       "news"),
    ("NVIDIA Q4 FY2027 earnings call transcript",    "news"),
    ("Revenue grew to $39.3B this quarter",          "news"),
    ("Operating income up 22% in latest filing",     "news"),
    ("10-Q filed with SEC",                          "news"),
    ("Quarterly earnings report disappoints",        "news"),
    # Expansion (NOT funding)
    ("NVIDIA investing in UK AI infrastructure",      "expansion"),
    ("Tesla investing $5B in new factory",            "expansion"),
    ("Stripe partnership with Shopify",               "expansion"),
    # Funding (real fundraising events)
    ("Anthropic raised $30 billion Series G",         "funding"),
    ("Affirm Series E at $22.5B valuation",           "funding"),
    ("startup raised Series B last week",             "funding"),
    ("Initial Public Offering filed today",           "funding"),
    ("seed funding round closed",                     "funding"),
    # Product (real launches, not earnings)
    ("Anthropic launches new Claude Pro model",       "product"),
    ("NVIDIA announces new Vera CPU",                 "product"),
    # Hiring
    ("OpenAI hiring 100 engineers",                   "hiring"),
    # Corporate disclosure / static content → news (NOT funding/product)
    ("Pertamina Sustainable Finance Framework published",  "news"),
    ("Sustainability Report 2025 — Telkomsel ESG goals",   "news"),
    ("Company Profile — overview and history",             "news"),
    ("Investor Relations page updated",                    "news"),
    ("Annual Report filed with regulator",                 "news"),
    ("ESG framework released",                             "news"),
    ("Corporate Governance disclosure",                    "news"),
])
def test_signal_classification(text: str, expected: str) -> None:
    assert _detect_signal(text) == expected, \
        f"For {text!r}: expected {expected!r}, got {_detect_signal(text)!r}"


# ── SOURCE AUTHORITY TIER ────────────────────────────────────────────────────

@pytest.mark.parametrize("domain, expected_tier", [
    # Known Tier-1
    ("bloomberg.com",          "tier-1"),
    ("wsj.com",                "tier-1"),
    ("prnewswire.com",         "tier-1"),
    # Known primary company domains
    ("ir.aboutamazon.com",     "tier-1"),
    ("aboutamazon.com",        "tier-1"),
    ("amazon.science",         "tier-1"),
    ("nvidianews.nvidia.com",  "tier-1"),
    ("anthropic.com",          "tier-1"),
    # Subdomain heuristic — primary-source prefixes anywhere
    ("investor.somecompany.com",   "tier-1"),
    ("news.somecompany.com",       "tier-1"),
    ("press.somecompany.com",      "tier-1"),
    ("corporate.somecompany.com",  "tier-1"),
    # Known Tier-2
    ("techcrunch.com",         "tier-2"),
    ("forbes.com",             "tier-2"),
    # Tier-3 fallback
    ("randomblog.io",          "tier-3"),
    ("facebook.com",           "tier-3"),
    # Edge cases
    ("",                       "tier-3"),
])
def test_source_tier_classification(domain: str, expected_tier: str) -> None:
    assert _classify_source_tier(domain) == expected_tier


# ── FRESHNESS DECAY ──────────────────────────────────────────────────────────

def test_freshness_keeps_recent_high() -> None:
    """Recent (<90 days) high-confidence evidence stays high."""
    from datetime import datetime, timedelta, timezone
    recent = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%b %d, %Y")
    assert _freshness_aware_confidence("high", recent) == "high"


def test_freshness_caps_old_at_low() -> None:
    """Year-old high-confidence evidence is capped to low."""
    from datetime import datetime, timedelta, timezone
    ancient = (datetime.now(timezone.utc) - timedelta(days=500)).strftime("%b %d, %Y")
    assert _freshness_aware_confidence("high", ancient) == "low"


def test_freshness_no_date_keeps_base() -> None:
    """If we can't parse a date, keep the base confidence."""
    assert _freshness_aware_confidence("high", None) == "high"
    assert _freshness_aware_confidence("medium", "") == "medium"
