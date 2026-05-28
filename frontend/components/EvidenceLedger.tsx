"use client";
import { useState } from "react";
import { Card, CardBody, CardHeader, CardTitle, Badge } from "./ui/primitives";
import type { Evidence, EvidenceMode } from "@/lib/types";
import { formatTimeAgo } from "@/lib/utils";
import { ExternalLink, ShieldCheck, Radio, AlertCircle } from "lucide-react";

type Filter = "all" | EvidenceMode;

export function EvidenceLedger({ evidence, evidenceHash }: { evidence: Evidence[]; evidenceHash?: string | null }) {
  const [filter, setFilter] = useState<Filter>("all");
  const liveCount = evidence.filter((e) => e.mode === "live").length;

  const filtered = filter === "all" ? evidence : evidence.filter((e) => e.mode === filter);

  return (
    <Card>
      <CardHeader className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <CardTitle>Evidence Ledger</CardTitle>
          {liveCount > 0 && (
            <Badge tone="positive">
              <Radio className="h-3 w-3 animate-pulse-dot" />
              {liveCount} live source{liveCount > 1 ? "s" : ""}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {/* Filter buttons */}
          <div className="flex items-center gap-1">
            {(["all", "live", "mock", "fallback"] as Filter[]).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-0.5 rounded text-[10px] uppercase tracking-wider transition ${
                  filter === f
                    ? "bg-accent/15 text-accent border border-accent/30"
                    : "text-ink-dim hover:text-ink-muted border border-transparent"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-ink-muted">
            <ShieldCheck className="h-3.5 w-3.5 text-accent" />
            Every claim is traceable
          </div>
        </div>
      </CardHeader>
      <CardBody className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-bg-elev/60 text-ink-muted text-[11px] uppercase tracking-wider border-b border-line">
              <tr>
                <th className="text-left font-normal px-4 py-2.5 w-8">#</th>
                <th className="text-left font-normal px-4 py-2.5">Source</th>
                <th className="text-left font-normal px-4 py-2.5">Signal</th>
                <th className="text-left font-normal px-4 py-2.5">Summary</th>
                <th className="text-left font-normal px-4 py-2.5">Tool</th>
                <th className="text-left font-normal px-4 py-2.5">Conf.</th>
                <th className="text-left font-normal px-4 py-2.5">Mode</th>
                <th className="text-left font-normal px-4 py-2.5">When</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((e) => (
                <Row key={e.id} e={e} />
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-[12px] text-ink-muted">
                    No {filter} evidence items found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {evidence.every((e) => e.mode === "mock") && (
          <div className="flex items-center gap-2 px-4 py-3 border-t border-line/60 bg-accent-warn/5 text-[12px] text-accent-warn">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            All evidence is demo data. Add{" "}
            <code className="font-mono text-xs">BRIGHT_DATA_API_TOKEN</code> to{" "}
            <code className="font-mono text-xs">.env</code> and set{" "}
            <code className="font-mono text-xs">USE_MOCK=false</code> for live data.
          </div>
        )}
        {evidenceHash && (
          <div className="flex items-center justify-between gap-2 px-4 py-2.5 border-t border-line/60 text-[10.5px] text-ink-dim font-mono"
            title="SHA256 of evidence payload + score values. Same evidence + same score means same hash.">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="h-3 w-3 text-accent" />
              Reproducibility hash
            </span>
            <span className="text-accent">{evidenceHash}</span>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function Row({ e }: { e: Evidence }) {
  return (
    <tr className="border-t border-line/60 hover:bg-bg-elev/40 transition-colors">
      <td className="px-4 py-3 text-ink-dim font-mono text-xs">#{e.id}</td>

      <td className="px-4 py-3 max-w-[200px]">
        {e.source_title ? (
          <div>
            {e.url ? (
              <a
                href={e.url}
                target="_blank"
                rel="noreferrer"
                className="text-[12.5px] text-ink hover:text-accent flex items-start gap-1.5 leading-tight"
              >
                <ExternalLink className="h-3 w-3 shrink-0 mt-0.5 text-ink-muted" />
                <span className="line-clamp-2">{e.source_title}</span>
              </a>
            ) : (
              <span className="text-[12.5px] text-ink leading-tight line-clamp-2">
                {e.source_title}
              </span>
            )}
            <div className="text-[10px] text-ink-dim mt-0.5 flex items-center gap-1.5">
              <span>{e.source}</span>
              {e.tier && <TierBadge tier={e.tier} />}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-ink text-[12.5px]">{e.source}</span>
            {e.tier && <TierBadge tier={e.tier} />}
            {e.url && (
              <a href={e.url} target="_blank" rel="noreferrer" className="text-ink-dim hover:text-ink">
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        )}
      </td>

      <td className="px-4 py-3 text-ink-muted text-[11px] uppercase tracking-wide">{e.signal}</td>
      <td className="px-4 py-3 text-ink-muted text-[12.5px] max-w-[380px] leading-relaxed">{e.summary}</td>

      <td className="px-4 py-3 whitespace-nowrap">
        <Badge tone="info">{e.tool}</Badge>
      </td>

      <td className="px-4 py-3">
        <Badge tone={e.confidence === "high" ? "positive" : e.confidence === "medium" ? "info" : "warn"}>
          {e.confidence}
        </Badge>
      </td>

      <td className="px-4 py-3 whitespace-nowrap">
        <ModeBadge mode={e.mode} />
      </td>

      <td className="px-4 py-3 text-ink-dim text-[11px] whitespace-nowrap">
        {formatTimeAgo(e.timestamp ?? null)}
      </td>
    </tr>
  );
}

function TierBadge({ tier }: { tier: NonNullable<Evidence["tier"]> }) {
  const meta = {
    "tier-1": { label: "T1", title: "Tier 1 — verified press / primary source (Bloomberg, WSJ, PR Newswire)", cls: "border-accent/40 text-accent bg-accent/10" },
    "tier-2": { label: "T2", title: "Tier 2 — established tech/business media (TechCrunch, Forbes, CRN)", cls: "border-line2 text-ink-muted bg-bg-elev" },
    "tier-3": { label: "T3", title: "Tier 3 — niche / aggregator / blog source", cls: "border-line text-ink-dim bg-transparent" },
  }[tier];
  return (
    <span
      title={meta.title}
      className={`inline-flex items-center font-mono text-[9px] px-1.5 py-0.5 rounded border ${meta.cls}`}
    >
      {meta.label}
    </span>
  );
}

function ModeBadge({ mode }: { mode: Evidence["mode"] }) {
  if (mode === "live") {
    return (
      <Badge tone="positive">
        <Radio className="h-3 w-3 animate-pulse-dot" /> live
      </Badge>
    );
  }
  if (mode === "fallback") {
    return <Badge tone="warn">fallback</Badge>;
  }
  return <Badge tone="neutral">demo</Badge>;
}
