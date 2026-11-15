"""Zero-dependency Model Context Protocol (MCP) stdio JSON-RPC 2.0 server for SautiMesh."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from sautimesh import __version__
from sautimesh.cascade import CascadeConfig
from sautimesh.dpg import generate_dpg_transparency_card, run_benchmark_suite
from sautimesh.engine import SautiMeshEngine
from sautimesh.languages import analyze_utterance

MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "sautimesh_analyze_utterance",
        "description": (
            "Analyze a spoken/typed utterance across Swahili, Luganda, Yoruba, Hausa, French, "
            "English, Pidgin, and Runyankole for code-switching spans, PII redaction, and SMS/USSD packing."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Utterance text to analyze."},
                "hint_language": {"type": "string", "description": "Optional ISO code hint (sw, lg, yo, ha, fr, en)."},
            },
            "required": ["text"],
        },
    },
    {
        "name": "sautimesh_run_voice_turn",
        "description": "Execute a full offline-first voice turn with cascade routing and SQLite persistence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "channel": {"type": "string", "default": "voice"},
                "currency_code": {"type": "string", "default": "UGX"},
                "offline_mode": {"type": "boolean", "default": True},
            },
            "required": ["text"],
        },
    },
    {
        "name": "sautimesh_run_benchmark",
        "description": "Run the built-in 7-case multilingual code-switching & escalation benchmark suite.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "sautimesh_sync_outbox",
        "description": "Inspect or flush pending offline store-and-forward queue messages.",
        "inputSchema": {
            "type": "object",
            "properties": {"dry_run": {"type": "boolean", "default": True}},
        },
    },
    {
        "name": "sautimesh_export_dpg_card",
        "description": "Export the DPGA Open Source AI Model & Limitation Card JSON.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def handle_mcp_request(
    request: dict[str, Any],
    db_path: str | Path = ".sautimesh/sautimesh.db",
) -> dict[str, Any] | None:
    """Process a single JSON-RPC 2.0 MCP message and return response dict (or None for notifications)."""
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params") or {}

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "sautimesh", "version": __version__},
                "capabilities": {"tools": {}},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}
    if method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            payload = _dispatch_tool(tool_name, args, db_path=db_path)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
                    "isError": False,
                },
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {exc}"}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def _dispatch_tool(
    name: str,
    args: dict[str, Any],
    db_path: str | Path,
) -> dict[str, Any]:
    if name == "sautimesh_analyze_utterance":
        text = str(args.get("text", "")).strip()
        if not text:
            raise ValueError("'text' must be a non-empty string.")
        hint = args.get("hint_language")
        return analyze_utterance(text, hint_language=str(hint) if hint else None).to_dict()

    if name == "sautimesh_run_voice_turn":
        text = str(args.get("text", "")).strip()
        engine = SautiMeshEngine(
            db_path=db_path,
            cascade_config=CascadeConfig(
                offline_mode=bool(args.get("offline_mode", True)),
                currency_code=str(args.get("currency_code", "UGX")),
            ),
        )
        return engine.run_turn(
            text=text,
            channel=str(args.get("channel", "voice")),
        ).to_dict()

    if name == "sautimesh_run_benchmark":
        return run_benchmark_suite()

    if name == "sautimesh_sync_outbox":
        engine = SautiMeshEngine(db_path=db_path)
        if args.get("dry_run", True):
            return {
                "metrics": engine.store.summary_metrics(),
                "pending_items": engine.store.list_outbox(limit=25),
            }
        return engine.store.sync_outbox()

    if name == "sautimesh_export_dpg_card":
        return generate_dpg_transparency_card()

    raise ValueError(f"Unknown MCP tool: {name}")


def serve_stdio(db_path: str | Path = ".sautimesh/sautimesh.db") -> None:
    """Serve newline-delimited JSON-RPC 2.0 MCP requests over stdin/stdout."""
    for line in sys.stdin:
        raw = line.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError as exc:
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()
            continue
        resp = handle_mcp_request(req, db_path=db_path)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
