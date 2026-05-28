"use client";
import { Card, CardBody, CardHeader, CardTitle, Badge, StatDot } from "./ui/primitives";
import type { InfraCall, ReportMode } from "@/lib/types";
import { Server, Globe2, Database, Unlock, Workflow, Radio } from "lucide-react";

const ICONS: Record<string, React.ReactNode> = {
  "SERP API": <Globe2 className="h-4 w-4" />,
  "Web Scraper API": <Database className="h-4 w-4" />,
  "Web Unlocker": <Unlock className="h-4 w-4" />,
  "Scraping Browser": <Server className="h-4 w-4" />,
  "MCP Server": <Workflow className="h-4 w-4" />,
};

const STATUS_LABEL: Record<string, string> = {
  ok: "live",
  cached: "pre-warmed snapshot",
  mock: "demo",
  fallback: "fallback",
  skipped: "skipped",
  error: "error",
  architecture: "wired · not active",
};

export function JudgeMode({ infra, mode, evidenceCount }: { infra: InfraCall[]; mode: ReportMode; evidenceCount: number }) {
  // Count both 'ok' (truly live) and 'cached' (pre-warmed snapshot) as actively serving data.
  const liveTools = infra.filter((i) => i.status === "ok" || i.status === "cached");
  const totalEvidence = evidenceCount;

  return (
    <Card className="border-accent/20">
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle>Bright Data Infrastructure Used</CardTitle>
          <div className="flex items-center gap-2">
            {liveTools.length > 0 && (
              <Badge tone="positive">
                <Radio className="h-3 w-3 animate-pulse-dot" />
                {liveTools.length} live tool{liveTools.length > 1 ? "s" : ""}
              </Badge>
            )}
            <Badge
              tone={
                mode === "live" ? "positive" :
                mode === "hybrid" ? "info" :
                mode === "fallback" ? "warn" : "neutral"
              }
            >
              {mode.toUpperCase()} MODE
            </Badge>
          </div>
        </div>

        {/* Summary bar */}
        <div className="flex items-center gap-4 mt-3 pt-3 border-t border-line/60 flex-wrap">
          <Stat label="Total evidence items" value={totalEvidence} />
          <Stat label="Tools called" value={infra.length} />
          <Stat label="Live calls" value={liveTools.length} tone="positive" />
          <div title="Sum of each tool's original fetch time. Cached responses serve from RAM in <10ms.">
            <Stat
              label="Cold-fetch sum"
              value={`${(infra.reduce((s, i) => s + (i.ms ?? 0), 0) / 1000).toFixed(1)}s`}
            />
          </div>
        </div>
      </CardHeader>

      <CardBody>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {infra.map((row, i) => (
            <ToolCard key={`${row.tool}-${i}`} row={row} />
          ))}
        </div>

        <p className="mt-4 text-[12px] text-ink-dim leading-relaxed border-t border-line/60 pt-4">
          SignalScout AI uses Bright Data&apos;s public-web data plane.{" "}
          {mode === "live" || mode === "hybrid" ? (
            <><strong className="text-ink-muted">SERP API</strong> is running two live concurrent queries —
            news + funding signals and competitor discovery.{" "}</>
          ) : (
            <><strong className="text-ink-muted">SERP API</strong> is wired for two concurrent queries
            and activates when <code className="font-mono text-[11px]">BRIGHT_DATA_API_TOKEN</code> is set.{" "}</>
          )}
          <strong className="text-ink-muted">Web Scraper API</strong> serves pre-warmed Bright Data snapshots
          of LinkedIn hiring data (pre-fetched at startup, not synchronously scraped);{" "}
          <strong className="text-ink-muted">Web Unlocker</strong> bypasses paywalls for full article text live.{" "}
          <strong className="text-ink-muted">MCP Server</strong> exposes our agent as a tool-callable endpoint
          via JSON-RPC 2.0 (the "USB-C for AI") — any Claude Desktop or MCP client can call us at{" "}
          <code className="font-mono text-[11px]">/mcp</code>.
        </p>
      </CardBody>
    </Card>
  );
}

function ToolCard({ row }: { row: InfraCall }) {
  const isLive = row.status === "ok";
  const isCached = row.status === "cached";
  const isArch = row.status === "architecture";
  return (
    <div
      className={`rounded-xl border p-4 flex items-start gap-3 transition ${
        isLive ? "border-accent/30 bg-accent/5"
        : isCached ? "border-accent2/30 bg-accent2/5"
        : isArch ? "border-line/40 bg-bg/20 opacity-60"
        : "border-line bg-bg-elev/60"
      }`}
    >
      <div className="rounded-md border border-line bg-bg-card p-2 text-ink shrink-0">
        {ICONS[row.tool] ?? <Server className="h-4 w-4" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <span className="text-[13px] text-ink font-medium">{row.tool}</span>
          <div className="flex items-center gap-2">
            {/* Evidence count */}
            {row.evidence_count > 0 && (
              <span className="text-[10px] text-ink-muted bg-bg-card border border-line rounded px-1.5 py-0.5">
                {row.evidence_count} evidence
              </span>
            )}
            {/* Status */}
            <div className="flex items-center gap-1 text-[11px] text-ink-muted">
              <StatDot tone={isLive || isCached ? "ok" : row.status === "error" ? "danger" : "mute"} />
              <span>{STATUS_LABEL[row.status] ?? row.status}</span>
              {row.ms > 0 && <span className="text-ink-dim">· {row.ms}ms</span>}
            </div>
          </div>
        </div>
        <p className="text-[12px] text-ink-muted mt-1 leading-snug">{row.purpose}</p>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
  tone?: "positive" | "neutral";
}) {
  const display =
    value === null || value === undefined || (typeof value === "number" && isNaN(value))
      ? "—"
      : String(value);

  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-ink-dim">{label}</div>
      <div
        className={`text-[18px] font-semibold leading-tight ${
          tone === "positive" ? "text-accent" : "text-ink"
        }`}
      >
        {display}
      </div>
    </div>
  );
}
