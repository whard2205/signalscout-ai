import type { AnalyzeResponse, TimelineEvent } from "./types";

// Local dev: /api is rewritten by next.config.js to http://localhost:8000.
// Production (Vercel): NEXT_PUBLIC_API_BASE MUST be set to the deployed
// backend URL (e.g. https://signalscout-backend.onrender.com). Without it
// the app cannot reach the backend.
const BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";

if (typeof window !== "undefined" && BASE === "/api" && process.env.NODE_ENV === "production") {
  // Loud client-side warning when deployed without env var configured.
  // eslint-disable-next-line no-console
  console.warn(
    "[SignalScout AI] NEXT_PUBLIC_API_BASE is not set. " +
    "API calls will hit /api which only works in local dev. " +
    "Set NEXT_PUBLIC_API_BASE to your deployed backend URL on Vercel."
  );
}

export async function analyzeOnce(company: string): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company }),
  });
  if (!res.ok) throw new Error(`analyze failed: ${res.status}`);
  return res.json();
}

export type StreamHandler = {
  onStep?: (e: { key: string; label: string; tool: string; mode?: string; ms?: number }) => void;
  onStepsFinal?: (steps: TimelineEvent[]) => void;
  onResult?: (r: AnalyzeResponse) => void;
  onError?: (err: Error) => void;
  onEnd?: () => void;
};

export function analyzeStream(company: string, h: StreamHandler) {
  const url = `${BASE}/analyze/stream?company=${encodeURIComponent(company)}`;
  const es = new EventSource(url);

  es.addEventListener("step", (e) => {
    try { h.onStep?.(JSON.parse((e as MessageEvent).data)); } catch {}
  });
  es.addEventListener("steps_final", (e) => {
    try { h.onStepsFinal?.(JSON.parse((e as MessageEvent).data).steps); } catch {}
  });
  es.addEventListener("result", (e) => {
    try { h.onResult?.(JSON.parse((e as MessageEvent).data)); } catch {}
  });
  es.addEventListener("end", () => { h.onEnd?.(); es.close(); });
  es.onerror = () => { h.onError?.(new Error("stream error")); es.close(); };

  return () => es.close();
}
