"""Deterministic mock data for demo-safe mode.

Seeded by company name → same input = same output every run.
All evidence has mode='mock' and source_title filled in.
Mock data is intentionally labeled as demo data in the UI.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Tuple

from app.models.schemas import (
    ActionPack,
    AnalyzeResponse,
    CompanyProfile,
    CompetitorRow,
    Evidence,
    InfraCall,
    Score,
    Scores,
    SignalCard,
)


def _seed(company: str) -> random.Random:
    h = int(hashlib.sha256(company.lower().encode()).hexdigest(), 16) % (2**32)
    return random.Random(h)


def _ts(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _profile(company: str, rng: random.Random) -> CompanyProfile:
    industries = ["B2B SaaS", "Fintech", "Cybersecurity", "DevTools", "Data Infrastructure", "MarTech"]
    sizes = ["51-200", "201-500", "501-1000", "1001-5000"]
    hqs = ["San Francisco, CA", "New York, NY", "London, UK", "Berlin, DE", "Singapore"]
    known_domains = {
        "bank central asia": "bca.co.id",
        "bca": "bca.co.id",
        "telkomsel": "telkomsel.com",
        "openai": "openai.com",
    }
    domain = known_domains.get(company.lower().strip(), f"{company.lower().replace(' ', '')}.com")
    return CompanyProfile(
        name=company,
        domain=domain,
        industry=rng.choice(industries),
        hq=rng.choice(hqs),
        size=rng.choice(sizes),
        description=(
            f"{company} provides modern infrastructure for fast-growing engineering teams. "
            "Active expansion phase detected. [DEMO DATA — not verified]"
        ),
    )


def _evidence(company: str, rng: random.Random) -> list[Evidence]:
    n = company.lower().replace(" ", "")
    return [
        Evidence(
            id="e1",
            source="linkedin.com",
            source_title=f"{company} — {rng.randint(18, 47)} open roles in Sales & RevOps",
            url=f"https://www.linkedin.com/company/{n}/jobs/",
            signal="hiring",
            summary=(
                f"[DEMO] {company} posted {rng.randint(18, 47)} new roles in the last 30 days, "
                "concentrated in Sales, Solutions Engineering, and RevOps. "
                "This is simulated data — wire Bright Data Web Scraper API for live data."
            ),
            timestamp=_ts(rng.randint(1, 6)),
            tool="Web Scraper API",
            confidence="medium",
            mode="mock",
        ),
        Evidence(
            id="e2",
            source="techcrunch.com",
            source_title=f"{company} raises Series C to accelerate enterprise GTM [DEMO]",
            url=None,
            signal="funding",
            summary=(
                "[DEMO] Reported Series C extension led by a tier-1 fund to accelerate enterprise GTM. "
                "This is simulated data — wire Bright Data SERP API for live news."
            ),
            timestamp=_ts(rng.randint(7, 20)),
            tool="SERP API",
            confidence="low",
            mode="mock",
        ),
        Evidence(
            id="e3",
            source=f"{n}.com",
            source_title=f"{company} Blog: Announcing enterprise tier [DEMO]",
            url=None,
            signal="product",
            summary=(
                "[DEMO] Enterprise-tier product launched targeting regulated industries. "
                "Wire Bright Data Web Unlocker to scrape the live blog."
            ),
            timestamp=_ts(rng.randint(3, 14)),
            tool="Web Unlocker",
            confidence="low",
            mode="mock",
        ),
        Evidence(
            id="e4",
            source="g2.com",
            source_title=f"{company} Reviews — onboarding friction reported [DEMO]",
            url=None,
            signal="review",
            summary=(
                "[DEMO] Recent reviews flag onboarding friction at scale. "
                "Wire Bright Data Web Scraper API for live G2 data."
            ),
            timestamp=_ts(rng.randint(2, 10)),
            tool="Web Scraper API",
            confidence="low",
            mode="mock",
        ),
        Evidence(
            id="e5",
            source="google.com/search",
            source_title="Competitor pricing change detected [DEMO]",
            url=None,
            signal="competitor",
            summary=(
                "[DEMO] Top competitor reduced annual pricing by ~15% and added a free enterprise trial. "
                "Wire Bright Data SERP API for live competitive intel."
            ),
            timestamp=_ts(rng.randint(1, 5)),
            tool="SERP API",
            confidence="low",
            mode="mock",
        ),
        Evidence(
            id="e6",
            source="linkedin.com/jobs",
            source_title=f"{company} Job Description — tech stack signals [DEMO]",
            url=None,
            signal="hiring",
            summary=(
                "[DEMO] Job posts reference Snowflake, dbt, Kafka, and internal ML platform. "
                "Wire Web Scraper API for real job description parsing."
            ),
            timestamp=_ts(rng.randint(1, 8)),
            tool="Web Scraper API",
            confidence="low",
            mode="mock",
        ),
        Evidence(
            id="e7",
            source="businesswire.com",
            source_title=f"{company} announces strategic cloud partnership [DEMO]",
            url=None,
            signal="expansion",
            summary=(
                "[DEMO] Strategic integration with a major cloud provider announced. "
                "Wire Bright Data SERP API to detect real partnership announcements."
            ),
            timestamp=_ts(rng.randint(10, 25)),
            tool="SERP API",
            confidence="low",
            mode="mock",
        ),
    ]


def _signals() -> list[SignalCard]:
    return [
        SignalCard(kind="hiring", title="Aggressive GTM hiring",
                   detail="Sales + RevOps headcount up sharply in last 30 days.",
                   impact="positive", evidence_ids=["e1", "e6"]),
        SignalCard(kind="funding", title="Fresh capital [Demo]",
                   detail="Reported Series C extension — budget cycle likely active.",
                   impact="positive", evidence_ids=["e2"]),
        SignalCard(kind="product", title="New enterprise tier [Demo]",
                   detail="Launch targets regulated buyers — expands ICP overlap.",
                   impact="positive", evidence_ids=["e3"]),
        SignalCard(kind="review", title="Scaling pains in onboarding [Demo]",
                   detail="Enterprise reviewers cite support latency.",
                   impact="negative", evidence_ids=["e4"]),
        SignalCard(kind="competitor", title="Competitor undercut pricing [Demo]",
                   detail="Discount + free trial pressuring deal cycles.",
                   impact="negative", evidence_ids=["e5"]),
        SignalCard(kind="expansion", title="Strategic cloud partnership [Demo]",
                   detail="Co-sell motion likely accelerates pipeline.",
                   impact="positive", evidence_ids=["e7"]),
    ]


def _competitors(rng: random.Random) -> list[CompetitorRow]:
    pool = [
        ("Hexlane", "Same buyer persona", "Cut annual price 15%", "high"),
        ("Mira Cloud", "Adjacent workload", "Launched free tier", "medium"),
        ("Northstack", "Overlaps on data layer", "New SOC2 Type II", "low"),
        ("Pulsegrid", "Shares ICP in fintech", "Hired former VP Sales", "medium"),
    ]
    rng.shuffle(pool)
    return [CompetitorRow(name=n, overlap=o, recent_move=m, threat=t) for n, o, m, t in pool[:3]]


def _exec_summary(company: str) -> Tuple[str, str]:
    summary = (
        f"{company} is showing a strong why-now profile based on public signals: "
        "an active hiring surge in revenue functions, reported funding, and a new enterprise tier — "
        "partially offset by competitor pricing pressure and onboarding feedback at scale. "
        "[Note: demo mode — wire Bright Data for verified live data.]"
    )
    why_now = (
        f"{company} is in an active GTM expansion window. Hiring + funding + new tier "
        "signals detected within the last 30 days. Reach out before the budget conversation closes."
    )
    return summary, why_now


def _infra_mock(evidence: list[Evidence]) -> list[InfraCall]:
    from collections import Counter
    tool_counts = Counter(e.tool for e in evidence)
    return [
        InfraCall(tool="SERP API", purpose="Live news + funding signal search",
                  status="mock", ms=0, evidence_count=tool_counts.get("SERP API", 0)),
        InfraCall(tool="Web Scraper API", purpose="LinkedIn jobs + G2 reviews",
                  status="mock", ms=0, evidence_count=tool_counts.get("Web Scraper API", 0)),
        InfraCall(tool="Web Unlocker", purpose="JS-rendered company blog",
                  status="mock", ms=0, evidence_count=tool_counts.get("Web Unlocker", 0)),
        InfraCall(tool="MCP Server", purpose="Agent orchestration",
                  status="mock", ms=0, evidence_count=tool_counts.get("MCP Server", 0)),
    ]


def _action_pack(company: str) -> ActionPack:
    return ActionPack(
        urgency="High",
        sales_angles=[
            f"Position around scaling enterprise onboarding — directly addresses the G2 pain.",
            f"Anchor ROI against the competitor discount: total cost of switching vs your value.",
            f"Lead with co-sell story leveraging their new cloud partnership.",
        ],
        cold_email=(
            f"Subject: Quick thought on {company}'s enterprise rollout\n\n"
            f"Hi {{first_name}},\n\n"
            f"Noticed {company} is leaning hard into enterprise — new tier, fresh hiring across "
            f"Sales and RevOps, and a recent cloud partnership. Teams hitting that stage usually "
            f"hit the same wall: onboarding friction at scale.\n\n"
            f"We help teams cut enterprise time-to-value without standing up a new ops team. "
            f"Worth a 15-minute look?\n\n"
            f"— {{your_name}}"
        ),
        linkedin_message=(
            f"Saw the recent moves at {company} — congrats on the new enterprise tier. "
            f"Curious how you're approaching onboarding at scale for the regulated segment. "
            f"Happy to share what we're seeing across similar teams if useful."
        ),
        discovery_questions=[
            "How are you currently scoping onboarding capacity for the new enterprise tier?",
            "Where does the competitor pricing move show up in your renewal conversations?",
            "Which signals from your new cloud partnership are you prioritizing for co-sell?",
        ],
    )


def build_mock_response(company: str) -> AnalyzeResponse:
    rng = _seed(company)
    profile = _profile(company, rng)
    evidence = _evidence(company, rng)
    signals = _signals()
    competitors = _competitors(rng)
    exec_summary, why_now_reason = _exec_summary(company)

    # Placeholder scores — will be recomputed by scoring.py
    placeholder_score = Score(value=0, label="", rationale="", confidence="low")
    scores = Scores(
        why_now=placeholder_score,
        buying_intent=placeholder_score,
        expansion_signal=placeholder_score,
        competitor_threat=placeholder_score,
    )

    return AnalyzeResponse(
        company=profile,
        executive_summary=exec_summary,
        why_now_reason=why_now_reason,
        scores=scores,
        signals=signals,
        competitors=competitors,
        evidence=evidence,
        action_pack=_action_pack(company),
        infra=_infra_mock(evidence),
        mode="mock",
        generated_at="",
    )
