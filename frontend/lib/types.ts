export type Confidence = "low" | "medium" | "high";
export type Urgency = "Low" | "Medium" | "High";
export type EvidenceMode = "live" | "mock" | "fallback";
export type SourceTier = "tier-1" | "tier-2" | "tier-3";
export type ReportMode = "live" | "mock" | "hybrid" | "fallback";
export type LLMProvider = "claude" | "mimo" | "none";
export type InfraStatus = "ok" | "mock" | "fallback" | "skipped" | "error" | "architecture" | "cached";
export type BrightDataTool =
  | "SERP API"
  | "Web Scraper API"
  | "Web Unlocker"
  | "Scraping Browser"
  | "MCP Server";

export type SignalKind =
  | "hiring" | "news" | "product" | "competitor"
  | "pricing" | "review" | "expansion" | "funding";

export interface Score {
  value: number;
  label: string;
  rationale: string;
  confidence: Confidence;
  components?: Record<string, number>; // why-now component breakdown
}

export interface Scores {
  why_now: Score;
  buying_intent: Score;
  expansion_signal: Score;
  competitor_threat: Score;
}

export interface Evidence {
  id: string;
  source: string;
  source_title?: string | null;       // actual article/page headline
  url?: string | null;
  signal: string;
  summary: string;
  timestamp?: string | null;
  tool: BrightDataTool;
  confidence: Confidence;
  mode: EvidenceMode;                 // live | mock | fallback
  tier?: SourceTier;                  // source authority badge
}

export interface SignalCard {
  kind: SignalKind;
  title: string;
  detail: string;
  impact: "positive" | "negative" | "neutral";
  evidence_ids: string[];
}

export interface CompetitorRow {
  name: string;
  overlap: string;
  recent_move: string;
  threat: "low" | "medium" | "high";
  mode?: EvidenceMode;
  source_url?: string | null;
  source_title?: string | null;
}

export interface CompanyProfile {
  name: string;
  domain?: string | null;
  industry?: string | null;
  hq?: string | null;
  size?: string | null;
  description?: string | null;
}

export interface ActionPack {
  urgency: Urgency;
  sales_angles: string[];
  cold_email: string;
  linkedin_message: string;
  discovery_questions: string[];
}

export interface InfraCall {
  tool: BrightDataTool;
  purpose: string;
  status: InfraStatus;
  ms: number;
  evidence_count: number;
}

export interface AnalyzeResponse {
  company: CompanyProfile;
  executive_summary: string;
  why_now_reason: string;
  scores: Scores;
  signals: SignalCard[];
  competitors: CompetitorRow[];
  evidence: Evidence[];
  action_pack: ActionPack;
  infra: InfraCall[];
  mode: ReportMode;
  llm_provider: LLMProvider;
  evidence_hash?: string | null;
  generated_at: string;
}

export interface TimelineEvent {
  key: string;
  label: string;
  tool: string;
  status: "pending" | "running" | "done" | "error";
  mode?: InfraStatus;
  ms?: number;
}
