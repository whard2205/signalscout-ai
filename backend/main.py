"""SignalScout AI — FastAPI entrypoint.

Run locally:
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.mcp_routes import router as mcp_router

load_dotenv()

log = logging.getLogger("signalscout.startup")

app = FastAPI(
    title="SignalScout AI",
    description=(
        "Why-Now Deal Intelligence Agent — powered by Bright Data + Claude. "
        "MCP-compatible: see /mcp and /mcp/health endpoints."
    ),
    version="0.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(mcp_router)


@app.get("/")
def root() -> dict:
    return {
        "service": "signalscout-ai",
        "docs": "/docs",
        "mcp_endpoint": "/mcp",
        "mcp_health": "/mcp/health",
        "transparency": "/transparency",
    }


@app.on_event("startup")
async def _auto_warmup() -> None:
    """Pre-cache hero companies in the background so the first demo click
    returns in ~6 milliseconds instead of ~13 seconds.

    Set AUTO_WARMUP=false in .env to disable (useful for local dev with no
    Bright Data quota).
    """
    if os.getenv("AUTO_WARMUP", "false").lower() not in {"1", "true", "yes"}:
        return

    # Fire-and-forget; never block app startup
    async def _run_warmup():
        try:
            # Wait a moment so the server is fully accepting traffic first
            await asyncio.sleep(2)
            from app.api.routes import _build_response, _cache_set, _cache_get

            heroes = ["NVIDIA", "Anthropic", "Affirm", "Walmart", "Marriott", "Amazon"]
            log.info("[warmup] pre-caching %d hero companies...", len(heroes))
            for company in heroes:
                if _cache_get(company) is not None:
                    continue
                try:
                    resp = await _build_response(company)
                    _cache_set(company, resp)
                    log.info("[warmup] %s ✓ mode=%s evidence=%d",
                             company, resp.mode, len(resp.evidence))
                except Exception as exc:
                    log.warning("[warmup] %s failed: %s", company, exc)
            log.info("[warmup] DONE — hero cache populated")
        except Exception as exc:
            log.warning("[warmup] crashed: %s", exc)

    asyncio.create_task(_run_warmup())
