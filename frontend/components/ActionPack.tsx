"use client";
import { useState } from "react";
import { Card, CardBody, CardHeader, CardTitle, Badge, Button } from "./ui/primitives";
import type { ActionPack as Pack } from "@/lib/types";
import { Copy, Check, Mail, Linkedin, Target, HelpCircle } from "lucide-react";

export function ActionPack({ pack, whyNowConfidence }: { pack: Pack; whyNowConfidence?: string }) {
  const isLowConf = whyNowConfidence === "low";
  return (
    <Card>
      <CardHeader className="flex items-center justify-between flex-wrap gap-2">
        <CardTitle>Action Pack</CardTitle>
        <div className="flex flex-col items-end gap-1">
          <Badge tone={pack.urgency === "High" ? "positive" : pack.urgency === "Medium" ? "info" : "warn"}>
            {isLowConf ? "Provisional urgency" : "Urgency"}: {pack.urgency}
          </Badge>
          {isLowConf && (
            <span className="text-[10px] text-accent-warn">
              low confidence · verify with live data
            </span>
          )}
        </div>
      </CardHeader>
      <CardBody className="space-y-5">
        <Section icon={<Target className="h-4 w-4" />} title="Sales angles">
          <ul className="space-y-2">
            {pack.sales_angles.map((a, i) => (
              <li key={i} className="text-[14px] text-ink-muted flex gap-3">
                <span className="text-accent">{String(i + 1).padStart(2, "0")}</span>
                <span>{a}</span>
              </li>
            ))}
          </ul>
        </Section>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <CopyBlock icon={<Mail className="h-4 w-4" />} title="Cold email" body={pack.cold_email} />
          <CopyBlock icon={<Linkedin className="h-4 w-4" />} title="LinkedIn message" body={pack.linkedin_message} />
        </div>

        <Section icon={<HelpCircle className="h-4 w-4" />} title="Discovery questions">
          <ul className="space-y-2">
            {pack.discovery_questions.map((q, i) => (
              <li key={i} className="text-[14px] text-ink-muted">
                <span className="text-accent mr-2">Q{i + 1}.</span>{q}
              </li>
            ))}
          </ul>
        </Section>
      </CardBody>
    </Card>
  );
}

function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-ink-muted mb-2">
        {icon}
        {title}
      </div>
      {children}
    </div>
  );
}

function CopyBlock({
  title,
  icon,
  body,
}: {
  title: string;
  icon: React.ReactNode;
  body: string;
}) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="rounded-xl border border-line bg-bg-elev/60">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-line/60">
        <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-ink-muted">
          {icon}
          {title}
        </div>
        <Button
          variant="ghost"
          className="!py-1 !px-2 text-xs"
          onClick={async () => {
            try {
              await navigator.clipboard.writeText(body);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            } catch {}
          }}
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      <pre className="px-4 py-3 text-[13px] text-ink whitespace-pre-wrap leading-relaxed font-sans">
{body}
      </pre>
    </div>
  );
}
