from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ----- Request -----

class AnalyzeRequest(BaseModel):
    company: str = Field(..., min_length=1)
    domain: Optional[str] = None
    fast_mode: bool = False


# ----- Evidence -----

BrightDataTool = Literal[
    "SERP API",
    "Web Scraper API",
    "Web Unlocker",
    "Scraping Browser",
    "MCP Server",
]

Confidence = Literal["low", "medium", "high"]
Urgency = Literal["Low", "Medium", "High"]
EvidenceMode = Literal["live", "mock", "fallback"]


SourceTier = Literal["tier-1", "tier-2", "tier-3"]


class Evidence(BaseModel):
    id: str
    source: str                          # domain or service name
    source_title: Optional[str] = None  # actual headline / page title
    url: Optional[str] = None
    signal: str                          # detected signal type
    summary: str
    timestamp: Optional[str] = None
    tool: BrightDataTool
    confidence: Confidence
    mode: EvidenceMode = "mock"          # live | mock | fallback
    tier: SourceTier = "tier-3"          # source authority (verified press > tech media > niche)


class SignalCard(BaseModel):
    kind: Literal[
        "hiring", "news", "product", "competitor", "pricing", "review", "expansion", "funding"
    ]
    title: str
    detail: str
    impact: Literal["positive", "negative", "neutral"] = "neutral"
    evidence_ids: List[str] = []


class CompetitorRow(BaseModel):
    name: str
    overlap: str
    recent_move: str
    threat: Literal["low", "medium", "high"]
    mode: EvidenceMode = "mock"
    source_url: Optional[str] = None
    source_title: Optional[str] = None


# ----- Scores -----

class Score(BaseModel):
    value: int = Field(..., ge=0, le=100)
    label: str
    rationale: str
    confidence: Confidence
    components: Optional[Dict[str, int]] = None  # breakdown per signal kind


class Scores(BaseModel):
    why_now: Score
    buying_intent: Score
    expansion_signal: Score
    competitor_threat: Score


# ----- Company profile -----

class CompanyProfile(BaseModel):
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    hq: Optional[str] = None
    size: Optional[str] = None
    description: Optional[str] = None


# ----- Action pack -----

class ActionPack(BaseModel):
    urgency: Urgency
    sales_angles: List[str]
    cold_email: str
    linkedin_message: str
    discovery_questions: List[str]


# ----- Infrastructure log (judge mode) -----

InfraStatus = Literal["ok", "mock", "fallback", "skipped", "error", "architecture", "cached", "partial"]


class InfraCall(BaseModel):
    tool: BrightDataTool
    purpose: str
    status: InfraStatus
    ms: int
    evidence_count: int = 0   # how many evidence items came from this tool


# ----- Full response -----

ReportMode = Literal["live", "mock", "hybrid", "fallback"]
LLMProvider = Literal["claude", "mimo", "none"]


class AnalyzeResponse(BaseModel):
    company: CompanyProfile
    executive_summary: str
    why_now_reason: str
    scores: Scores
    signals: List[SignalCard]
    competitors: List[CompetitorRow]
    evidence: List[Evidence]
    action_pack: ActionPack
    infra: List[InfraCall]
    mode: ReportMode
    llm_provider: LLMProvider = "none"
    evidence_hash: Optional[str] = None  # SHA256 of evidence payload + score values
    generated_at: str
