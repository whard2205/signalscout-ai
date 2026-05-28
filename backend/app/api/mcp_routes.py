"""MCP (Model Context Protocol) server endpoints.

Implements MCP JSON-RPC 2.0 protocol over HTTP so any MCP-compatible client
(Claude Desktop, ChatGPT plugins, custom agents, Bright Data MCP middleware)
can call SignalScout AI as a tool.

Spec reference: https://spec.modelcontextprotocol.io/specification/

Exposed tools:
1. analyze_company(name) → full Why-Now intelligence report
2. get_evidence(company, signal_kind?) → filter evidence rows by signal type
3. compare_companies(a, b) → side-by-side score delta with attribution

Quick verify (after backend running):

    # initialize
    curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
      -d '{"jsonrpc":"2.0","id":1,"method":"initialize",
           "params":{"protocolVersion":"2024-11-05","capabilities":{}}}'

    # list tools
    curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
      -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'

    # call a tool
    curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
      -d '{"jsonrpc":"2.0","id":3,"method":"tools/call",
           "params":{"name":"analyze_company","arguments":{"name":"NVIDIA"}}}'
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


router = APIRouter()


# ── MCP protocol metadata ───────────────────────────────────────────────────

MCP_PROTOCOL_VERSION = "2024-11-05"
MCP_SERVER_NAME = "signalscout-ai"
MCP_SERVER_VERSION = "0.5.0"

TOOLS_SPEC = [
    {
        "name": "analyze_company",
        "description": (
            "Run the full SignalScout AI Why-Now intelligence pipeline for one "
            "company. Fires Bright Data SERP API (×2) and Web Unlocker live in "
            "request for news/funding/product signals, competitor discovery, and "
            "full article text extraction. Hiring data is loaded from a "
            "pre-warmed Bright Data Web Scraper snapshot if available (fresh "
            "Web Scraper jobs are triggered out-of-band via /warmup or "
            "/scraper/refresh, never blocking /analyze). Returns deterministic "
            "scores from scoring.py (research-informed heuristic, not LLM) plus "
            "an LLM-synthesized executive summary."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Company name, e.g. 'NVIDIA' or 'Walmart'.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_evidence",
        "description": (
            "Return live evidence rows for a company, optionally filtered by "
            "signal kind. Each row links to the source URL pulled from Bright "
            "Data — fully auditable."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name."},
                "signal_kind": {
                    "type": "string",
                    "description": "Optional filter: hiring|funding|product|news|expansion|competitor|review|pricing.",
                },
            },
            "required": ["company"],
        },
    },
    {
        "name": "compare_companies",
        "description": (
            "Compare two companies side-by-side. Returns score deltas across "
            "Why-Now / Buying Intent / Expansion / Competitor Threat dimensions, "
            "plus attribution of which signal kinds drive the difference."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "string", "description": "First company name."},
                "b": {"type": "string", "description": "Second company name."},
            },
            "required": ["a", "b"],
        },
    },
]


# ── JSON-RPC dispatcher ─────────────────────────────────────────────────────

def _rpc_result(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _rpc_error(req_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


async def _handle_initialize(req_id: Any, params: dict) -> dict:
    return _rpc_result(req_id, {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {
            "tools": {"listChanged": False},
            "logging": {},
        },
        "serverInfo": {
            "name": MCP_SERVER_NAME,
            "version": MCP_SERVER_VERSION,
        },
    })


async def _handle_tools_list(req_id: Any, params: dict) -> dict:
    return _rpc_result(req_id, {"tools": TOOLS_SPEC})


async def _handle_tools_call(req_id: Any, params: dict) -> dict:
    name = params.get("name", "")
    args = params.get("arguments", {}) or {}

    # Lazy import to avoid circular dependency at module load.
    from app.api.routes import _build_response, _cache_get, _cache_set, compare

    try:
        if name == "analyze_company":
            company = args.get("name", "").strip()
            if not company:
                return _rpc_error(req_id, -32602, "Missing 'name' argument")
            cached = _cache_get(company)
            if cached is None:
                cached = await _build_response(company)
                _cache_set(company, cached)
            text = json.loads(cached.model_dump_json())
            return _rpc_result(req_id, {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "company": text["company"]["name"],
                        "mode": text["mode"],
                        "scores": {
                            k: text["scores"][k]["value"]
                            for k in ["why_now", "buying_intent",
                                      "expansion_signal", "competitor_threat"]
                        },
                        "evidence_hash": text.get("evidence_hash"),
                        "executive_summary": text["executive_summary"],
                        "why_now_reason": text["why_now_reason"],
                        "evidence_count": len(text["evidence"]),
                        "live_evidence_count": sum(
                            1 for e in text["evidence"] if e.get("mode") == "live"
                        ),
                    }, ensure_ascii=False),
                }],
                "isError": False,
            })

        if name == "get_evidence":
            company = args.get("company", "").strip()
            signal_filter = args.get("signal_kind")
            if not company:
                return _rpc_error(req_id, -32602, "Missing 'company' argument")
            cached = _cache_get(company)
            if cached is None:
                cached = await _build_response(company)
                _cache_set(company, cached)
            evidence = [
                {
                    "id": e.id, "source": e.source, "title": e.source_title,
                    "url": e.url, "signal": e.signal, "tool": e.tool,
                    "tier": e.tier, "confidence": e.confidence, "mode": e.mode,
                    "summary": e.summary[:200],
                }
                for e in cached.evidence
                if signal_filter is None or e.signal == signal_filter
            ]
            return _rpc_result(req_id, {
                "content": [{
                    "type": "text",
                    "text": json.dumps({
                        "company": cached.company.name,
                        "filter": signal_filter,
                        "evidence": evidence,
                    }, ensure_ascii=False),
                }],
                "isError": False,
            })

        if name == "compare_companies":
            a = args.get("a", "").strip()
            b = args.get("b", "").strip()
            if not a or not b:
                return _rpc_error(req_id, -32602, "Both 'a' and 'b' required")
            result = await compare(a=a, b=b)
            return _rpc_result(req_id, {
                "content": [{
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False),
                }],
                "isError": False,
            })

        return _rpc_error(req_id, -32601, f"Unknown tool: {name}")

    except Exception as exc:  # safety net
        return _rpc_error(req_id, -32603, f"Internal error: {exc}")


@router.post("/mcp")
async def mcp_jsonrpc(request: Request) -> JSONResponse:
    """MCP JSON-RPC 2.0 endpoint. Dispatches initialize / tools/list / tools/call."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={
            "jsonrpc": "2.0", "id": None,
            "error": {"code": -32700, "message": "Parse error"},
        })

    if not isinstance(body, dict):
        return JSONResponse(content=_rpc_error(None, -32600, "Invalid Request"))

    req_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {}) or {}

    dispatchers = {
        "initialize":  _handle_initialize,
        "tools/list":  _handle_tools_list,
        "tools/call":  _handle_tools_call,
        # 'notifications/initialized' is a one-way notification — ack with empty result
        "notifications/initialized": lambda rid, p: _rpc_result(rid, {}),
        "ping": lambda rid, p: _rpc_result(rid, {}),
    }

    handler = dispatchers.get(method)
    if not handler:
        return JSONResponse(content=_rpc_error(req_id, -32601, f"Method not found: {method}"))

    if asyncio.iscoroutinefunction(handler):
        return JSONResponse(content=await handler(req_id, params))
    return JSONResponse(content=handler(req_id, params))


@router.get("/mcp/health")
async def mcp_health() -> dict:
    """Lightweight reachability check used by the infra log."""
    return {
        "status": "ok",
        "protocol": MCP_PROTOCOL_VERSION,
        "server": MCP_SERVER_NAME,
        "version": MCP_SERVER_VERSION,
        "tools_count": len(TOOLS_SPEC),
        "tools": [t["name"] for t in TOOLS_SPEC],
    }
