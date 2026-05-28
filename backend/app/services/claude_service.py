"""Claude synthesis layer.

Takes raw collected signals + evidence and returns a structured intelligence
report. If ANTHROPIC_API_KEY is missing, we degrade to the mock generator so
the demo never breaks. The prompt enforces "No-BS AI Mode":

- never invent facts
- when evidence is thin, return "Unknown" / "Insufficient evidence"
- always tie claims to evidence IDs
- keep the generated overlay short

Default model is Claude Haiku 4.5 to keep demo costs and latency low. Override
with ANTHROPIC_MODEL if a higher-quality model is needed.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

try:
    from anthropic import Anthropic
except Exception:  # pragma: no cover - optional dep at import time
    Anthropic = None  # type: ignore


DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TOKENS = 1200


def _model() -> str:
    return os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _max_tokens() -> int:
    raw = os.getenv("ANTHROPIC_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)).strip()
    try:
        return max(300, min(int(raw), 1800))
    except ValueError:
        return DEFAULT_MAX_TOKENS


SYSTEM_PROMPT = """You are SignalScout AI — a no-BS enterprise GTM intelligence analyst.

Hard rules:
1. Never invent facts. If a signal is not in the provided evidence, do not claim it.
2. If something is uncertain, say "Unknown" or "Insufficient evidence".
3. Every claim must be traceable to one or more evidence IDs from the input list.
4. Output compact JSON only and match the requested schema exactly.
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


def is_configured() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY")) and Anthropic is not None


def synthesize(company: str, signals: list[dict], evidence: list[dict]) -> Optional[dict[str, Any]]:
    """Run Claude synthesis. Returns None if not configured or on failure.

    The caller is responsible for merging this output with the deterministic
    scoring layer and falling back to mock when None is returned.
    """
    if not is_configured():
        return None

    client = Anthropic()
    prompt_payload = {
        "company": company,
        "signals": signals,
        "evidence": evidence,
        "instructions": (
            "Return JSON with keys: executive_summary, why_now_reason, "
            "action_pack {urgency, sales_angles[], cold_email, linkedin_message, "
            "discovery_questions[]}."
        ),
    }

    try:
        resp = client.messages.create(
            model=_model(),
            max_tokens=_max_tokens(),
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": json.dumps(prompt_payload),
            }],
        )
        text = "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")
        # Be defensive: extract the first JSON object in the response.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        return json.loads(text[start : end + 1])
    except Exception:
        return None
