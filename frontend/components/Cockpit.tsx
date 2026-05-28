"use client";
import { useEffect, useRef, useState } from "react";
import { Search, Sparkles, Radio, Building2, Copy, Check } from "lucide-react";
import { Card, CardBody, Button, Badge } from "./ui/primitives";
import { AgentTimeline } from "./AgentTimeline";
import { WhyNowScore } from "./WhyNowScore";
import { SignalGrid } from "./SignalGrid";
import { EvidenceLedger } from "./EvidenceLedger";
import { ActionPack } from "./ActionPack";
import { AuditTrail } from "./AuditTrail";
import { CompetitorTable } from "./CompetitorTable";
import { JudgeMode } from "./JudgeMode";
import { analyzeOnce, analyzeStream } from "@/lib/api";
import type { AnalyzeResponse, TimelineEvent } from "@/lib/types";

const SUGGESTIONS = ["NVIDIA", "Anthropic", "Affirm", "Walmart", "Marriott", "Amazon"];

const PIPELINE: TimelineEvent[] = [
  { key: "serp",   label: "News Discovery Agent — SERP API for funding & launch signals",  tool: "SERP API",        status: "pending" },
  { key: "comp",   label: "Competitor Mapping Agent — SERP API for alternatives query",    tool: "SERP API",        status: "pending" },
  { key: "scrape", label: "Hiring Intel Agent — pre-warmed Bright Data Web Scraper snapshot", tool: "Web Scraper API", status: "pending" },
  { key: "unlock", label: "Deep Read Agent — Web Unlocker bypasses paywall + JS render",   tool: "Web Unlocker",    status: "pending" },
  { key: "mcp",    label: "MCP Server — JSON-RPC 2.0 endpoint live ('USB-C for AI' tool surface)", tool: "MCP Server",      status: "pending" },
  { key: "score",  label: "Scoring Agent — deterministic scoring.py + test-covered",       tool: "scoring",         status: "pending" },
  { key: "synth",  label: "Synthesis Agent — Claude generates the why-now narrative",      tool: "Claude",          status: "pending" },
];

export function Cockpit() {
  const [company, setCompany] = useState("");
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [report, setReport] = useState<AnalyzeResponse | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const stopRef = useRef<null | (() => void)>(null);
  const gotResultRef = useRef(false);
  const fallbackRef = useRef(false);

  function start(name: string) {
    const target = name.trim();
    if (!target || running) return;
    setRunning(true);
    setReport(null);
    setNotice(null);
    gotResultRef.current = false;
    fallbackRef.current = false;
    setEvents(PIPELINE.map((p, i) => ({ ...p, status: i === 0 ? "running" : "pending" })));

    const runFallback = async () => {
      if (fallbackRef.current || gotResultRef.current) return;
      fallbackRef.current = true;
      setNotice("Streaming was interrupted; completing with the direct analysis endpoint.");
      try {
        const result = await analyzeOnce(target);
        gotResultRef.current = true;
        setReport(result);
        setEvents((prev) => prev.map((e) => ({ ...e, status: "done" })));
      } catch {
        setNotice("Analysis failed. Check that the deployed backend URL and environment variables are configured.");
        setEvents((prev) => prev.map((e) => e.status === "running" ? { ...e, status: "error" } : e));
      } finally {
        setRunning(false);
      }
    };

    stopRef.current?.();
    stopRef.current = analyzeStream(target, {
      onStep: (step) => {
        setEvents((prev) => {
          const idx = prev.findIndex((e) => e.key === step.key);
          if (idx === -1) return prev;
          const next = [...prev];
          next[idx] = { ...next[idx], status: "done" };
          if (idx + 1 < next.length) next[idx + 1] = { ...next[idx + 1], status: "running" };
          return next;
        });
      },
      // steps_final replaces the simulated timeline with real latency + mode per tool
      onStepsFinal: (steps) => {
        setEvents(steps.map((s) => ({ ...s, status: "done" as const })));
      },
      onResult: (r) => {
        gotResultRef.current = true;
        setReport(r);
      },
      onEnd: () => {
        if (gotResultRef.current) {
          setRunning(false);
        } else {
          void runFallback();
        }
      },
      onError: () => { void runFallback(); },
    });
  }

  useEffect(() => () => stopRef.current?.(), []);

  return (
    <div className="min-h-screen">
      <TopBar />
      <main className="container max-w-7xl py-8 space-y-6">
        <Hero
          company={company}
          setCompany={setCompany}
          onRun={() => start(company)}
          onRunWith={start}
          running={running}
        />
        {notice && <RuntimeNotice message={notice} />}

        <div className="grid grid-cols-1 lg:grid-cols-[1fr,360px] gap-6">
          <div className="space-y-6">
            {report ? (
              <>
                <ExecSummary report={report} />
                <WhyNowScore scores={report.scores} reason={report.why_now_reason} />
                <SignalGrid signals={report.signals} />
                <AuditTrail signals={report.signals} evidence={report.evidence} scores={report.scores} />
                <CompetitorTable rows={report.competitors} />
                <EvidenceLedger evidence={report.evidence} evidenceHash={report.evidence_hash} />
                <ActionPack pack={report.action_pack} whyNowConfidence={report.scores.why_now.confidence} />
                <JudgeMode infra={report.infra} mode={report.mode} evidenceCount={report.evidence.length} />
              </>
            ) : (
              <EmptyState />
            )}
          </div>

          <aside className="space-y-6 lg:sticky lg:top-6 self-start">
            <AgentTimeline events={events} active={running} />
            <DemoTips />
          </aside>
        </div>

        <Footer />
      </main>
    </div>
  );
}

function RuntimeNotice({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-accent-warn/25 bg-accent-warn/10 px-4 py-3 text-[12.5px] text-accent-warn">
      {message}
    </div>
  );
}


function TopBar() {
  return (
    <header className="border-b border-line/60 bg-bg/80 backdrop-blur sticky top-0 z-40">
      <div className="container max-w-7xl flex items-center justify-between py-3">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-accent/15 border border-accent/30 grid place-items-center">
            <Radio className="h-4 w-4 text-accent" />
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight">SignalScout AI</div>
            <div className="text-[11px] text-ink-muted -mt-0.5">
              Evidence-First Why-Now Engine
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge tone="info">
            <Sparkles className="h-3 w-3" /> Powered by Bright Data + Claude
          </Badge>
        </div>
      </div>
    </header>
  );
}

function Hero({
  company,
  setCompany,
  onRun,
  onRunWith,
  running,
}: {
  company: string;
  setCompany: (s: string) => void;
  onRun: () => void;
  onRunWith: (name: string) => void;
  running: boolean;
}) {
  return (
    <Card className="relative overflow-hidden">
      <div className="absolute inset-0 grid-fade opacity-50" aria-hidden />
      <CardBody className="relative py-8">
        <div className="max-w-2xl">
          <div className="text-[11px] uppercase tracking-[0.18em] text-ink-muted">
            GTM Intelligence Cockpit
          </div>
          <h1 className="mt-2 text-3xl md:text-4xl font-semibold leading-tight">
            Why should we contact this company <span className="text-accent">right now?</span>
          </h1>
          <p className="mt-3 text-ink-muted max-w-xl">
            Enter any company. SignalScout pulls live web data through Bright Data and returns
            a why-now report where every score is computable and every claim has a source.
          </p>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              onRun();
            }}
            className="mt-6 flex items-stretch gap-2"
          >
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-dim" />
              <input
                value={company}
                onChange={(e) => setCompany(e.target.value)}
                placeholder="e.g. Ramp, Snowflake, Vercel…"
                className="w-full rounded-lg bg-bg-elev border border-line pl-9 pr-3 py-3 text-[15px] text-ink placeholder:text-ink-dim focus:outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/15"
                disabled={running}
              />
            </div>
            <Button type="submit" disabled={running}>
              {running ? "Analyzing…" : "Run Intelligence"}
            </Button>
          </form>

          <div className="mt-3 flex items-center gap-2 flex-wrap">
            <span className="text-[11px] text-ink-dim uppercase tracking-wider">Try:</span>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => { setCompany(s); onRunWith(s); }}
                disabled={running}
                className="chip hover:text-ink hover:border-line/90 transition disabled:opacity-50"
              >
                <Building2 className="h-3 w-3" /> {s}
              </button>
            ))}
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

const MODE_META: Record<string, { label: string; tone: "positive" | "info" | "warn" | "neutral"; hint: string }> = {
  live:     { label: "LIVE",     tone: "positive", hint: "Bright Data + LLM — verified live data" },
  hybrid:   { label: "HYBRID",   tone: "info",     hint: "Live SERP + LLM synthesis" },
  fallback: { label: "FALLBACK", tone: "warn",     hint: "Live attempt failed — using demo data" },
  mock:     { label: "DEMO",     tone: "neutral",  hint: "Demo data — add BRIGHT_DATA_API_TOKEN for live" },
};

function ExecSummary({ report }: { report: AnalyzeResponse }) {
  const meta = MODE_META[report.mode] ?? MODE_META.mock;
  const liveCount = report.evidence.filter((e) => e.mode === "live").length;

  return (
    <Card>
      <CardBody>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-muted">Target</div>
            <div className="mt-1 flex items-baseline gap-3">
              <span className="text-2xl font-semibold">{report.company.name}</span>
              {report.company.domain && (
                <span className="text-ink-dim text-sm">{report.company.domain}</span>
              )}
            </div>
            <div className="mt-1 text-[12px] text-ink-muted flex flex-wrap gap-x-3 gap-y-1">
              {report.company.industry && <span>{report.company.industry}</span>}
              {report.company.size && <span>· {report.company.size} employees</span>}
              {report.company.hq && <span>· {report.company.hq}</span>}
            </div>
            {report.mode === "mock" && (
              <div className="mt-1.5 text-[10px] text-ink-dim">
                Demo profile · industry / size / HQ not verified live
              </div>
            )}
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <Badge tone={meta.tone}>{meta.label} MODE</Badge>
            <span className="text-[10px] text-ink-dim">{meta.hint}</span>
            {liveCount > 0 && (
              <span className="text-[10px] text-accent">{liveCount} live evidence items</span>
            )}
            <CopyBriefButton report={report} />
          </div>
        </div>
        <div className="mt-4 flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-ink-muted flex-wrap">
          <Sparkles className="h-3 w-3 text-accent" />
          <span>Synthesized by {providerLabel(report.llm_provider)} · evidence-grounded</span>
          <span className="text-ink-dim">· scores deterministic (scoring.py)</span>
          {report.generated_at && (
            <span className="text-ink-dim ml-auto">
              Generated {formatRelativeNow(report.generated_at)}
            </span>
          )}
        </div>
        <p className="mt-2 text-[15px] leading-relaxed text-ink">{report.executive_summary}</p>
      </CardBody>
    </Card>
  );
}

function providerLabel(provider: AnalyzeResponse["llm_provider"]): string {
  if (provider === "claude") return "Claude";
  if (provider === "mimo") return "MiMo";
  return "deterministic fallback";
}

function formatRelativeNow(iso: string): string {
  try {
    const t = new Date(iso).getTime();
    const diff = Math.max(0, (Date.now() - t) / 1000);
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  } catch {
    return "just now";
  }
}

// ── Copy GTM Brief ──────────────────────────────────────────────────────────
// Generates a plain-text brief from whatever AnalyzeResponse data is available.
// Works for ANY company. Gracefully handles missing fields:
//   - no Web Scraper snapshot → omitted from brief, no error
//   - missing url/source_title → those lines skipped
//   - missing action pack fields → labelled "—"
// Honest about modes: preserves the actual e.mode/tool wording.

function buildGtmBrief(report: AnalyzeResponse): string {
  const r = report;
  const sc = r.scores;

  const lines: string[] = [];
  lines.push(`SignalScout GTM Brief — ${r.company.name}`);
  if (r.company.domain) lines.push(`Domain: ${r.company.domain}`);
  lines.push("");
  lines.push(`Why-Now Score:        ${sc.why_now.value}/100  (confidence: ${sc.why_now.confidence})`);
  lines.push(`Buying Intent:        ${sc.buying_intent.value}/100  (${sc.buying_intent.confidence})`);
  lines.push(`Expansion Signal:     ${sc.expansion_signal.value}/100  (${sc.expansion_signal.confidence})`);
  lines.push(`Competitor Threat:    ${sc.competitor_threat.value}/100  (${sc.competitor_threat.confidence})`);
  lines.push("");
  lines.push(`Mode:                 ${r.mode}`);
  if (r.llm_provider && r.llm_provider !== "none") {
    lines.push(`LLM Provider:         ${r.llm_provider}`);
  }
  if (r.evidence_hash) {
    lines.push(`Evidence Hash:        ${r.evidence_hash}  (deterministic — same evidence → same hash)`);
  }
  lines.push("");

  // Top 3 evidence rows (live first, then any). Honest about source/tool/mode.
  const sortedEv = [...r.evidence].sort((a, b) => {
    const liveBias = (x: typeof a) => (x.mode === "live" ? 0 : 1);
    return liveBias(a) - liveBias(b);
  });
  const top3 = sortedEv.slice(0, 3);
  if (top3.length > 0) {
    lines.push("Top Evidence:");
    top3.forEach((e, i) => {
      const title = e.source_title || e.summary?.slice(0, 80) || "(no title)";
      lines.push(`  ${i + 1}. [${e.signal}] ${title}`);
      lines.push(`     Source: ${e.source}  (mode: ${e.mode}${e.tier ? ", " + e.tier : ""})`);
      lines.push(`     Tool:   ${e.tool}`);
      if (e.url) lines.push(`     URL:    ${e.url}`);
    });
    lines.push("");
  }

  // Best sales angle (first one — they're already ranked)
  const angle0 = r.action_pack?.sales_angles?.[0];
  if (angle0) {
    lines.push("Best Sales Angle:");
    lines.push(`  ${angle0}`);
    lines.push("");
  }

  // Cold email
  if (r.action_pack?.cold_email) {
    lines.push("Cold Email:");
    lines.push(r.action_pack.cold_email);
    lines.push("");
  }

  // Why-Now reason (the punchy sentence)
  if (r.why_now_reason) {
    lines.push("Why Now:");
    lines.push(`  ${r.why_now_reason}`);
    lines.push("");
  }

  lines.push(`— Generated ${formatRelativeNow(r.generated_at)} · SignalScout AI`);
  return lines.join("\n");
}

function CopyBriefButton({ report }: { report: AnalyzeResponse }) {
  const [copied, setCopied] = useState(false);
  const onClick = async () => {
    try {
      const brief = buildGtmBrief(report);
      await navigator.clipboard.writeText(brief);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard API unavailable (rare). Show "Copied" anyway so user knows
      // the click registered; brief is still in DOM for manual select if needed.
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    }
  };
  return (
    <Button
      variant="ghost"
      className="!py-1 !px-2.5 !text-[11px] mt-1"
      onClick={onClick}
      title="Copy a plain-text GTM brief of this analysis to clipboard"
    >
      {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Copied" : "Copy GTM Brief"}
    </Button>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardBody className="py-16 text-center">
        <div className="mx-auto h-12 w-12 rounded-xl border border-line bg-bg-elev grid place-items-center">
          <Sparkles className="h-5 w-5 text-accent" />
        </div>
        <div className="mt-4 text-ink font-medium">No analysis yet</div>
        <p className="mt-1 text-ink-muted text-sm max-w-md mx-auto">
          Enter a company above. The cockpit will stream live agent steps as Bright Data
          collects signals and Claude synthesizes the why-now report.
        </p>
      </CardBody>
    </Card>
  );
}

function DemoTips() {
  return (
    <Card>
      <CardBody className="text-[12.5px] text-ink-muted leading-relaxed">
        <div className="text-[11px] uppercase tracking-[0.16em] text-ink mb-2">
          Recommended Flow
        </div>
        <ol className="list-decimal pl-4 space-y-1">
          <li>Enter a company and watch live evidence collection.</li>
          <li>Review the deterministic Why-Now score.</li>
          <li>Open the Evidence Ledger to verify claims.</li>
          <li>Inspect Bright Data infrastructure usage.</li>
          <li>Copy the action pack for outreach.</li>
        </ol>
      </CardBody>
    </Card>
  );
}

function Footer() {
  return (
    <div className="text-center text-[11px] text-ink-dim pt-6">
      Evidence-First Why-Now Engine · Every score is computable · Every claim has a source · Built for Bright Data Web Data UNLOCKED
    </div>
  );
}
