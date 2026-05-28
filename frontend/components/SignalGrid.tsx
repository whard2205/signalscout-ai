"use client";
import { Card, CardBody, CardHeader, CardTitle, Badge } from "./ui/primitives";
import type { SignalCard } from "@/lib/types";
import {
  Briefcase, Newspaper, Rocket, Swords,
  Tag, MessageSquare, TrendingUp, Coins,
} from "lucide-react";

const ICONS: Record<string, React.ReactNode> = {
  hiring: <Briefcase className="h-4 w-4" />,
  news: <Newspaper className="h-4 w-4" />,
  product: <Rocket className="h-4 w-4" />,
  competitor: <Swords className="h-4 w-4" />,
  pricing: <Tag className="h-4 w-4" />,
  review: <MessageSquare className="h-4 w-4" />,
  expansion: <TrendingUp className="h-4 w-4" />,
  funding: <Coins className="h-4 w-4" />,
};

export function SignalGrid({ signals }: { signals: SignalCard[] }) {
  // Hide synthetic competitive-density rows ("comp_density_N") from the visual
  // grid — they're scoring-only contributions, kept in the Evidence Ledger
  // and Audit Trail for transparency but would otherwise clutter the panel
  // with 5 near-identical "Competitive pressure" tiles. Filter is keyed off
  // the backend's evidence_ids prefix so it stays in sync with routes.py.
  const visibleSignals = signals.filter(
    (s) => !(s.kind === "pricing" && s.evidence_ids?.some((id) => id.startsWith("comp_density_")))
  );
  const hiddenDensity = signals.length - visibleSignals.length;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Signal Intelligence</CardTitle>
      </CardHeader>
      <CardBody>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {visibleSignals.map((s) => (
            <SignalTile key={s.title} s={s} />
          ))}
        </div>
        {hiddenDensity > 0 && (
          <div className="mt-3 text-[10.5px] text-ink-dim italic">
            +{hiddenDensity} competitive-density signal{hiddenDensity !== 1 ? "s" : ""} included in scoring (see Evidence Ledger &middot; <code className="font-mono text-[10px]">comp_density_*</code>).
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function SignalTile({ s }: { s: SignalCard }) {
  const tone =
    s.impact === "positive" ? "positive" :
    s.impact === "negative" ? "danger" : "neutral";

  return (
    <div className="rounded-xl border border-line bg-bg-elev/60 p-4 hover:border-line/90 transition">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-ink-muted">
          <span className="rounded-md border border-line bg-bg-card p-1.5 text-ink">
            {ICONS[s.kind] ?? <Newspaper className="h-4 w-4" />}
          </span>
          <span className="text-[10px] uppercase tracking-wider">{s.kind}</span>
        </div>
        <Badge tone={tone as any}>{s.impact}</Badge>
      </div>
      <div className="mt-3 text-[14px] text-ink font-medium">{s.title}</div>
      <p className="mt-1 text-[13px] text-ink-muted leading-relaxed">{s.detail}</p>
      {s.evidence_ids?.length ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {s.evidence_ids.map((id) => (
            <span key={id} className="kbd">#{id}</span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
