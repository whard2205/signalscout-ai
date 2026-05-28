"""MiMo (Xiaomi) synthesis layer — backup LLM provider.

Used as fallback when Claude is unconfigured, rate-limited, or out of credit.
Same interface as claude_service: is_configured() + synthesize() returning
dict | None. Returning None lets the caller continue down the fallback chain
(mock executive_summary). Never raises.

Assumes an OpenAI-compatible chat completions endpoint, which is the standard
for Chinese LLM API platforms. Base URL and model are env-configurable so we
can correct without code changes if the platform diverges.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

import httpx


SYSTEM_PROMPT = """You are SignalScout AI — a no-BS enterprise GTM intelligence analyst.

Hard rules:
1. Never invent facts. If a signal is not in the provided evidence, do not claim it.
2. If something is uncertain, say "Unknown" or "Insufficient evidence".
3. Every claim must be traceable to one or more evidence IDs from the input list.
4. Always emit explicit confidence ("low", "medium", "high") on every score.
5. Output JSON only — match the requested schema exactly.

Voice & length:
- Tone: tight, sales-ops, evidence-first. No hype. No hallucinated metrics.
- executive_summary: 2–3 sentences max. Lead with the one concrete fact that
  changed (funding amount, valuation jump, new hire wave). Never hedge with
  "appears to" or "may be" if evidence is firm. Cap ~350 chars.
- why_now_reason: ONE punchy sentence. <=180 chars. Format: "[Concrete fact].
  [Specific implication for outreach]." Example: "Ramp just raised $500M at
  $22.5B. Procurement is hiring — 60-day buying window."
- action_pack.cold_email: <=120 words. Open with the concrete fact from
  evidence. Soft CTA, no fake urgency.

You are answering one question: "Why should a sales/GTM team contact this company right now?"
"""


def _base_url() -> str:
    return os.getenv("MIMO_BASE_URL", "https://api.xiaomimimo.com/v1").rstrip("/")


def _model() -> str:
    return os.getenv("MIMO_MODEL", "mimo-v2.5")


def is_configured() -> bool:
    return bool(os.getenv("MIMO_API_KEY"))


def synthesize(company: str, signals: list[dict], evidence: list[dict]) -> Optional[dict[str, Any]]:
    """Run MiMo synthesis. Returns None if not configured or on any failure."""
    if not is_configured():
        return None

    prompt_payload = {
        "company": company,
        "signals": signals,
        "evidence": evidence,
        "instructions": (
            "Return JSON with keys: executive_summary, why_now_reason, "
            "scores {why_now, buying_intent, expansion_signal, competitor_threat} "
            "(each has value 0-100, label, rationale, confidence), "
            "action_pack {urgency, sales_angles[], cold_email, linkedin_message, "
            "discovery_questions[]}."
        ),
    }

    url = f"{_base_url()}/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('MIMO_API_KEY', '')}",
        "Content-Type": "application/json",
    }
    body = {
        "model": _model(),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(prompt_payload)},
        ],
        "temperature": 0.2,
        "max_tokens": 1800,
        "response_format": {"type": "json_object"},
    }

    try:
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, headers=headers, json=body)
        if resp.status_code >= 400:
            return None
        data = resp.json()
        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if not text:
            return None
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        return json.loads(text[start : end + 1])
    except Exception:
        return None
