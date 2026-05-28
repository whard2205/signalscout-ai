"use client";
import { Card, CardBody, CardHeader, CardTitle } from "./ui/primitives";
import type { TimelineEvent } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Radio } from "lucide-react";

export function AgentTimeline({
  events,
  active,
}: {
  events: TimelineEvent[];
  active: boolean;
}) {
  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Agent Pipeline</CardTitle>
        <div className="flex items-center gap-2 text-[11px] text-ink-muted">
          {active ? (
            <>
              <Radio className="h-3 w-3 text-accent animate-pulse-dot" />
              Running
            </>
          ) : events.length > 0 ? (
            <>
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              Done
            </>
          ) : (
            <>
              <span className="h-1.5 w-1.5 rounded-full bg-ink-dim" />
              Idle
            </>
          )}
        </div>
      </CardHeader>
      <CardBody className="space-y-0.5 p-3">
        {events.length === 0 && (
          <div className="text-sm text-ink-muted py-4 text-center">
            Enter a company to begin live intelligence collection.
          </div>
        )}
        {events.map((e, i) => (
          <Row key={e.key} ev={e} index={i} isLast={i === events.length - 1} />
        ))}
      </CardBody>
    </Card>
  );
}

function Row({ ev, index, isLast }: { ev: TimelineEvent; index: number; isLast: boolean }) {
  const dot =
    ev.status === "done"    ? "bg-accent"
    : ev.status === "running" ? "bg-accent-info animate-pulse-dot"
    : ev.status === "error"   ? "bg-accent-danger"
    : "bg-line border border-ink-dim";

  const modeTone =
    ev.mode === "ok"        ? "text-accent"
    : ev.mode === "mock"    ? "text-ink-dim"
    : ev.mode === "fallback" ? "text-accent-warn"
    : ev.mode === "error"   ? "text-accent-danger"
    : "text-ink-dim";

  return (
    <div
      className="flex items-start gap-3 py-1.5 animate-fade-up"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      {/* Dot + connector */}
      <div className="relative pt-[5px] w-4 shrink-0 flex justify-center">
        <span className={cn("inline-block h-2 w-2 rounded-full", dot)} />
        {!isLast && (
          <span className="absolute top-4 left-1/2 -translate-x-1/2 w-px bg-line"
            style={{ height: "calc(100% + 6px)" }} aria-hidden />
        )}
      </div>

      {/* Label + meta */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <span className={cn(
            "text-[12.5px] leading-tight",
            ev.status === "done" ? "text-ink" : "text-ink-muted",
          )}>
            {ev.label}
          </span>
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-[10px] uppercase tracking-wider text-ink-dim">{ev.tool}</span>
          {ev.mode && ev.status === "done" && (
            <span className={cn("text-[10px]", modeTone)}>
              · {ev.mode === "ok" ? "live"
                : ev.mode === "cached" ? "pre-warmed snapshot"
                : ev.mode === "mock" ? (
                    ev.key === "synth" ? "LLM-synthesized"
                    : ev.key === "score" ? "deterministic"
                    : "ready"
                  )
                : ev.mode === "architecture" ? "wired · not active"
                : ev.mode}
              {ev.ms && ev.ms > 0 ? ` · ${ev.ms < 1000 ? ev.ms + "ms" : (ev.ms / 1000).toFixed(1) + "s"}` : ""}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
