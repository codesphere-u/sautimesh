"""Command-line interface for SautiMesh."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Sequence

from sautimesh import __version__
from sautimesh.audio import analyze_wav, synthesize_tone_wav
from sautimesh.cascade import CascadeConfig
from sautimesh.dpg import (
    format_dpg_markdown,
    generate_dpg_transparency_card,
    run_benchmark_suite,
)
from sautimesh.engine import SautiMeshEngine
from sautimesh.languages import SUPPORTED_LANGUAGES, analyze_utterance
from sautimesh.mcp_server import serve_stdio
from sautimesh.web_server import run_web_server


def build_parser() -> argparse.ArgumentParser:
    """Construct the SautiMesh CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="sautimesh",
        description="Voice-first, offline-first multilingual AI agent runtime for Africa & the global edge.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--db", default=".sautimesh/sautimesh.db", help="Path to SQLite store.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="Analyze utterance languages, code-switching, and packet limits.")
    p_analyze.add_argument("text", help="Utterance text to inspect.")
    p_analyze.add_argument("--lang", default=None, help="Optional language hint (sw, lg, yo, ha, fr, en).")

    p_chat = sub.add_parser("chat", help="Execute a full offline-first voice turn.")
    p_chat.add_argument("--text", default=None, help="Direct text or ASR transcript.")
    p_chat.add_argument("--wav", default=None, help="Path to 16-bit PCM WAV voice input.")
    p_chat.add_argument("--out-wav", default=None, help="Optional output WAV path for TTS audio.")
    p_chat.add_argument("--channel", default="voice", help="Channel name (voice, whatsapp_voice, sms, ussd).")
    p_chat.add_argument("--currency", default="UGX", help="Local currency for budget tracking.")
    p_chat.add_argument("--online", action="store_true", help="Allow local SLM or cloud escalation if configured.")

    p_synth = sub.add_parser("synth-sample", help="Generate a 16kHz PCM WAV sample for offline testing.")
    p_synth.add_argument("output_wav", help="Destination WAV file path.")
    p_synth.add_argument("--text", default="Habari daktari mtoto ana fever", help="Sample text.")

    sub.add_parser("eval", help="Run built-in code-switching & escalation benchmark suite.")
    sub.add_parser("sync", help="Flush pending store-and-forward outbox messages.")

    p_dpg = sub.add_parser("dpg-card", help="Export Digital Public Goods Open AI transparency card.")
    p_dpg.add_argument("--format", choices=["json", "markdown"], default="json")

    sub.add_parser("doctor", help="Inspect Python runtime, SQLite store, and optional Speech/LLM tools.")

    p_serve = sub.add_parser("serve", help="Start the local interactive SautiMesh Voice Workbench server.")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)

    sub.add_parser("mcp", help="Run stdio JSON-RPC 2.0 MCP server.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run SautiMesh CLI command and return process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        result = analyze_utterance(args.text, hint_language=args.lang)
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    if args.command == "synth-sample":
        out = synthesize_tone_wav(args.output_wav, text=args.text)
        stats = analyze_wav(out)
        print(json.dumps({"wav": str(out), "stats": stats.to_dict()}, indent=2))
        return 0

    if args.command == "chat":
        engine = SautiMeshEngine(
            db_path=args.db,
            cascade_config=CascadeConfig(
                offline_mode=not args.online,
                currency_code=args.currency,
            ),
        )
        turn = engine.run_turn(
            text=args.text,
            wav_path=args.wav,
            channel=args.channel,
            output_wav_path=args.out_wav,
        )
        print(json.dumps(turn.to_dict(), indent=2))
        return 0

    if args.command == "eval":
        report = run_benchmark_suite()
        print(json.dumps(report, indent=2))
        return 0 if report["passed_cases"] == report["total_cases"] else 1

    if args.command == "sync":
        engine = SautiMeshEngine(db_path=args.db)
        print(json.dumps(engine.store.sync_outbox(), indent=2))
        return 0

    if args.command == "dpg-card":
        if args.format == "markdown":
            print(format_dpg_markdown())
        else:
            print(json.dumps(generate_dpg_transparency_card(), indent=2))
        return 0

    if args.command == "doctor":
        engine = SautiMeshEngine(db_path=args.db)
        report = {
            "sautimesh_version": __version__,
            "python_version": sys.version.split()[0],
            "sqlite_db": str(Path(args.db)),
            "supported_languages": sorted(SUPPORTED_LANGUAGES),
            "optional_binaries": {
                "whisper-cli": shutil.which("whisper-cli") is not None,
                "piper": shutil.which("piper") is not None,
                "ollama": shutil.which("ollama") is not None,
            },
            "metrics": engine.store.summary_metrics(),
        }
        print(json.dumps(report, indent=2))
        return 0

    if args.command == "serve":
        server = run_web_server(host=args.host, port=args.port, db_path=args.db)
        print(f"SautiMesh Voice Workbench listening on http://{args.host}:{args.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0

    if args.command == "mcp":
        serve_stdio(db_path=args.db)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
