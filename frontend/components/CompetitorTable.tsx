"use client";
import { Card, CardBody, CardHeader, CardTitle, Badge, StatDot } from "./ui/primitives";
import type { CompetitorRow } from "@/lib/types";
import { Radio, ExternalLink, AlertCircle } from "lucide-react";

export function CompetitorTable({ rows }: { rows: CompetitorRow[] }) {
  const liveCount = rows.filter((r) => r.mode === "live").length;
  const allMock = rows.length > 0 && rows.every((r) => !r.mode || r.mode === "mock");

  return (
    <Card>
      <CardHeader className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <CardTitle>Competitive Landscape</CardTitle>
          {liveCount > 0 && (
            <Badge tone="positive">
              <Radio className="h-3 w-3 animate-pulse-dot" />
              {liveCount} live
            </Badge>
          )}
        </div>
        <div className="text-[10px] text-ink-dim uppercase tracking-wider">
          {rows.length === 0 ? "no data" : `${rows.length} competitor${rows.length !== 1 ? "s" : ""}`}
        </div>
      </CardHeader>
      <CardBody className="p-0">
        {rows.length === 0 ? (
          <div className="flex items-center gap-2 px-4 py-6 text-[12px] text-ink-muted">
            <AlertCircle className="h-4 w-4 shrink-0 text-accent-warn" />
            Insufficient evidence — no competitor signals found in live SERP results.
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead className="bg-bg-elev/60 text-ink-muted text-[11px] uppercase tracking-wider">
                <tr>
                  <th className="text-left font-normal px-4 py-2.5">Competitor</th>
                  <th className="text-left font-normal px-4 py-2.5">Overlap</th>
                  <th className="text-left font-normal px-4 py-2.5">Recent signal</th>
                  <th className="text-left font-normal px-4 py-2.5">Threat</th>
                  <th className="text-left font-normal px-4 py-2.5">Source</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.name} className="border-t border-line/60 hover:bg-bg-elev/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <StatDot tone={r.mode === "live" ? "ok" : "mute"} />
                        <span className="text-ink font-medium text-[13px]">{r.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-ink-muted text-[12px]">{r.overlap}</td>
                    <td className="px-4 py-3 text-ink-muted text-[12px] max-w-[240px]">
                      <span className="line-clamp-2">{r.recent_move}</span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={r.threat === "high" ? "danger" : r.threat === "medium" ? "warn" : "info"}>
                        {r.threat}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      {r.source_url ? (
                        <a
                          href={r.source_url}
                          target="_blank"
                          rel="noreferrer"
                          title={r.source_title ?? undefined}
                          className="text-ink-dim hover:text-accent transition"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      ) : (
                        <span className="text-[10px] text-ink-dim">demo</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {allMock && (
              <div className="flex items-center gap-2 px-4 py-2.5 border-t border-line/60 bg-bg-elev/40 text-[11px] text-ink-dim">
                <AlertCircle className="h-3 w-3 shrink-0" />
                Demo data — competitor SERP query activates with{" "}
                <code className="font-mono text-[10px]">BRIGHT_DATA_API_TOKEN</code>
              </div>
            )}
          </>
        )}
      </CardBody>
    </Card>
  );
}
