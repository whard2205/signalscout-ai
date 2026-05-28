"use client";
import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { Card, CardBody, Badge } from "./ui/primitives";
import type { Scores } from "@/lib/types";

function ring(value: number, tone: string) {
  return {
    background: `conic-gradient(${tone} ${value * 3.6}deg, rgba(255,255,255,0.06) 0deg)`,
  };
}

function toneFor(v: number) {
  if (v >= 75) return "#7cf0c8";
  if (v >= 55) return "#6aa9ff";
  if (v >= 35) return "#ffb547";
  return "#ff6b6b";
}

const COMPONENT_LABELS: Record<string, string> = {
  hiring_signal: "Hiring signal",
  news_momentum: "News momentum",
  product_launch: "Product launch",
  competitor_pressure: "Competitor pressure",
  review_pain: "Review pain",
  funding_or_partnership: "Funding / partnership",
};

export function WhyNowScore({ scores, reason }: { scores: Scores; reason: string }) {
  const v = scores.why_now.value;
  const tone = toneFor(v);
  const components = scores.why_now.components;

  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 grid-fade opacity-40" aria-hidden />
      <CardBody className="relative space-y-5">

        {/* ── Row 1: ring + reason ── */}
        <div className="flex flex-col sm:flex-row sm:items-start gap-6">

          {/* Score ring */}
          <div className="flex items-center gap-4 shrink-0">
            <div className="relative h-28 w-28 rounded-full" style={ring(v, tone)}>
              <div className="absolute inset-[6px] rounded-full bg-bg-card border border-line flex items-center justify-center">
                <div className="text-center">
                  <div className="text-[9px] tracking-[0.18em] text-ink-muted uppercase">Why-Now</div>
                  <div className="text-[36px] font-semibold leading-none mt-0.5" style={{ color: tone }}>
                    {v}
                  </div>
                  <div className="text-[9px] text-ink-muted uppercase tracking-wider">/100</div>
                </div>
              </div>
            </div>
            <div className="space-y-1.5">
              <div className="text-[10px] uppercase tracking-[0.18em] text-ink-muted">Live Buying Window</div>
              <Badge tone={v >= 75 ? "positive" : v >= 55 ? "info" : "warn"}>
                Confidence: {scores.why_now.confidence}
              </Badge>
              <p className="text-[12.5px] text-ink-muted leading-snug max-w-[220px]">
                {scores.why_now.rationale}
              </p>
            </div>
          </div>

          {/* Reason */}
          <div className="flex-1 sm:pl-6 sm:border-l border-line min-w-0">
            <div className="text-[10px] uppercase tracking-[0.18em] text-ink-muted mb-2">
              Reason to act now
            </div>
            <p className="text-[15px] leading-relaxed text-ink">{reason}</p>
          </div>
        </div>

        {/* ── Row 2: sub-scores as horizontal bars ── */}
        <div className="border-t border-line/60 pt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <ScoreBar label="Buying Intent"      v={scores.buying_intent.value}      c={scores.buying_intent.confidence} />
          <ScoreBar label="Expansion Signal"   v={scores.expansion_signal.value}   c={scores.expansion_signal.confidence} />
          <ScoreBar label="Competitor Threat"  v={scores.competitor_threat.value}  c={scores.competitor_threat.confidence} warn />
        </div>

        {/* ── Row 3: score breakdown (explainable AI) ── */}
        {components && Object.keys(components).length > 0 && (
          <div className="border-t border-line/60 pt-4">
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <div className="text-[10px] uppercase tracking-[0.18em] text-ink-muted">
                Why-Now Score Breakdown — deterministic, tune-able per pipeline
              </div>
              <div className="text-[10px] text-ink-dim">
                Research-informed heuristic · ordering from <span className="text-accent">Trigger Event Selling</span>,
                <span className="text-accent"> 6sense</span>, <span className="text-accent">Forrester</span> · tunable in code
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {Object.entries(components).map(([key, val]) => (
                <ComponentRow
                  key={key}
                  label={COMPONENT_LABELS[key] ?? key.replace(/_/g, " ")}
                  value={val}
                />
              ))}
            </div>
          </div>
        )}

        {/* ── Row 4: formula panel ── */}
        <FormulaPanel />
      </CardBody>
    </Card>
  );
}

// Per-signal positioning — each weight maps to a B2B intent-data framework
// that ORDERS this signal kind, not a claim about exact numeric calibration.
const SIGNAL_CITATIONS: Record<string, { weight: string; cite: string; cite_short: string }> = {
  hiring:     { weight: "0.18", cite: "Operational expansion trigger — treated as strong context, not a vendor-calibrated intent score",                  cite_short: "GTM heuristic" },
  funding:    { weight: "0.22", cite: "Trigger Event Selling (Elias) — funding/leadership change as high-value timing triggers",                         cite_short: "Elias" },
  product:    { weight: "0.18", cite: "Product launch / category activity — mapped to buyer-journey and intent-data frameworks",                         cite_short: "6sense/Demandbase" },
  news:       { weight: "0.10", cite: "Awareness-stage activity — content/news consumption is a lower-weight context signal",                            cite_short: "Demandbase" },
  expansion:  { weight: "0.10", cite: "Demand-unit / account expansion framing — mid-weight until stronger intent appears",                              cite_short: "Forrester" },
  competitor: { weight: "0.08", cite: "Competitive evaluation context — weighted mainly in competitor_threat, not why_now",                               cite_short: "B2B GTM" },
};

const RESEARCH_REFS = [
  {
    short: "Elias",
    full:  "Trigger Event Selling — Craig Elias",
    note:  "Framework around timing-based selling and trigger events (funding, leadership change).",
  },
  {
    short: "6sense",
    full:  "6sense intent-data documentation",
    note:  "Buying-stage framing: accounts move from awareness to purchase based on observed research/activity signals.",
  },
  {
    short: "Forrester",
    full:  "Forrester / SiriusDecisions Demand Unit Waterfall",
    note:  "B2B revenue framework separating awareness signals from late-funnel intent.",
  },
  {
    short: "Demandbase",
    full:  "Demandbase intent-data overview",
    note:  "B2B intent-data vendor documentation on awareness-stage signals.",
  },
  {
    short: "Bombora",
    full:  "Bombora Company Surge intent-data overview",
    note:  "B2B intent-data co-op describing account-level topic research and content-consumption surges.",
  },
];


function FormulaPanel() {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-line/60 pt-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-[10px] uppercase tracking-[0.16em] text-ink-dim hover:text-ink-muted transition"
      >
        How is this score computed? <span className="text-accent">+ research basis</span>
        <ChevronDown
          className={`h-3 w-3 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="mt-3 rounded-lg bg-bg-elev border border-line p-4 font-mono text-[11px] text-ink-muted space-y-4">
          {/* Formula */}
          <div className="text-accent">
            score = Σ weight(signal) × impact × confidence_boost × mode_multiplier
          </div>

          {/* Weights + per-signal citations */}
          <div>
            <div className="text-[9px] uppercase tracking-wider text-ink-dim mb-2">
              Signal weights (why-now dimension) — each tied to a B2B intent framework
            </div>
            <div className="space-y-1.5">
              {Object.entries(SIGNAL_CITATIONS).map(([signal, c]) => (
                <div key={signal} className="flex items-start gap-2 text-[10.5px]">
                  <span className="w-[68px] text-ink-dim flex-shrink-0">{signal}</span>
                  <span className="text-ink-dim">→</span>
                  <span className="text-ink w-10 flex-shrink-0">{c.weight}</span>
                  <span className="text-ink-dim flex-1 leading-snug">{c.cite}</span>
                  <span className="text-accent text-[9px] flex-shrink-0 mt-0.5">[{c.cite_short}]</span>
                </div>
              ))}
            </div>
          </div>

          {/* Mode + Confidence multipliers (smaller, since less debated) */}
          <div className="grid grid-cols-2 gap-4 text-[10px]">
            <div>
              <div className="text-[9px] uppercase tracking-wider text-ink-dim mb-1.5">Mode multiplier</div>
              <div className="flex gap-3 flex-wrap">
                {([["live","1.20×"],["mock","1.00×"],["fallback","0.90×"]] as const).map(([k,v]) => (
                  <span key={k}><span className="text-ink-dim">{k}</span> <span className="text-ink">{v}</span></span>
                ))}
              </div>
            </div>
            <div>
              <div className="text-[9px] uppercase tracking-wider text-ink-dim mb-1.5">Confidence boost</div>
              <div className="flex gap-3 flex-wrap">
                {([["high","1.00×"],["medium","0.85×"],["low","0.60×"]] as const).map(([k,v]) => (
                  <span key={k}><span className="text-ink-dim">{k}</span> <span className="text-ink">{v}</span></span>
                ))}
              </div>
            </div>
          </div>

          {/* Citations block — full references */}
          <div className="border-t border-line pt-3">
            <div className="text-[9px] uppercase tracking-wider text-ink-dim mb-2">
              Frameworks that inform the ordering (not exact calibration)
            </div>
            <div className="space-y-2">
              {RESEARCH_REFS.map((r) => (
                <div key={r.short} className="text-[10px] leading-snug">
                  <span className="text-accent">[{r.short}]</span>{" "}
                  <span className="text-ink">{r.full}</span>
                  <div className="text-ink-dim mt-0.5 ml-1">{r.note}</div>
                </div>
              ))}
            </div>
            <div className="text-[9px] text-ink-dim mt-2 italic">
              Full references with links in METHODOLOGY.md.
            </div>
          </div>

          {/* Footer */}
          <div className="text-[9px] text-ink-dim border-t border-line pt-2 leading-relaxed flex items-start justify-between gap-3 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              All numbers computed in{" "}
              <span className="text-ink-muted">backend/app/services/scoring.py</span>
              {" "}— never generated by the LLM. Weights are exposed so sales-ops teams can
              audit and tune per their own historical conversion data.
            </div>
            <div className="text-accent whitespace-nowrap font-mono text-[10px]"
              title="Test-covered: determinism, boundedness, ordering, and BrightDataClient method surface — see backend/tests/">
              ✓ test-covered
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ScoreBar({
  label, v, c, warn = false,
}: {
  label: string; v: number; c: string; warn?: boolean;
}) {
  const color = warn ? "#ffb547" : toneFor(v);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-ink-muted">{label}</span>
        <div className="flex items-baseline gap-0.5">
          <span className="text-[15px] font-semibold" style={{ color }}>{v}</span>
          <span className="text-[9px] text-ink-dim">/100</span>
          <span className="text-[9px] text-ink-dim ml-1.5">· {c}</span>
        </div>
      </div>
      <div className="h-1.5 w-full rounded-full bg-line overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${v}%`, background: color }}
        />
      </div>
    </div>
  );
}

function ComponentRow({ label, value }: { label: string; value: number }) {
  const color = toneFor(value);
  return (
    <div className="flex items-center gap-3">
      <span className="text-[11px] text-ink-muted w-40 shrink-0">{label}</span>
      <div className="flex-1 h-1 rounded-full bg-line overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${value}%`, background: color }}
        />
      </div>
      <span className="text-[11px] w-6 text-right shrink-0" style={{ color }}>
        {value}
      </span>
    </div>
  );
}
