"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("card shadow-card", className)} {...props} />;
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 pt-4 pb-3 border-b border-line/60", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("text-[12px] uppercase tracking-[0.14em] text-ink-muted", className)}
      {...props}
    />
  );
}

export function CardBody({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("p-5", className)} {...props} />;
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "ghost";
};
export function Button({ className, variant = "primary", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition",
        "focus:outline-none focus:ring-2 focus:ring-accent/40 disabled:opacity-50 disabled:cursor-not-allowed",
        variant === "primary"
          ? "bg-accent text-bg hover:brightness-110 shadow-glow"
          : "border border-line text-ink hover:bg-bg-elev",
        className,
      )}
      {...props}
    />
  );
}

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: "neutral" | "positive" | "warn" | "danger" | "info";
  className?: string;
  children: React.ReactNode;
}) {
  const tones: Record<string, string> = {
    neutral: "text-ink-muted border-line bg-bg-elev",
    positive: "text-accent border-accent/30 bg-accent/10",
    warn: "text-accent-warn border-accent-warn/30 bg-accent-warn/10",
    danger: "text-accent-danger border-accent-danger/30 bg-accent-danger/10",
    info: "text-accent-info border-accent-info/30 bg-accent-info/10",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] tracking-wide",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function StatDot({ tone }: { tone: "ok" | "warn" | "danger" | "mute" }) {
  const map: Record<string, string> = {
    ok: "bg-accent",
    warn: "bg-accent-warn",
    danger: "bg-accent-danger",
    mute: "bg-ink-dim",
  };
  return <span className={cn("inline-block h-1.5 w-1.5 rounded-full", map[tone])} />;
}
