"""Local Voice Workbench HTTP API and static website server."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sautimesh import __version__
from sautimesh.cascade import CascadeConfig
from sautimesh.dpg import generate_dpg_transparency_card, run_benchmark_suite
from sautimesh.engine import SautiMeshEngine
from sautimesh.languages import analyze_utterance

MAX_JSON_BODY_BYTES = 64 * 1024


def create_handler(
    db_path: Path,
    static_dir: Path | None = None,
) -> type[BaseHTTPRequestHandler]:
    """Bind request handler class with database path and optional static website root."""

    class SautiMeshRequestHandler(BaseHTTPRequestHandler):
        """Serve JSON telemetry/voice endpoints and static SautiMesh web workbench."""

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return  # Keep terminal output quiet for test harness & background runs

        def _send_json(self, code: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _read_json_body(self) -> dict[str, Any]:
            length_hdr = self.headers.get("Content-Length", "0")
            try:
                content_len = min(int(length_hdr), MAX_JSON_BODY_BYTES)
            except ValueError:
                return {}
            if content_len <= 0:
                return {}
            raw = self.rfile.read(content_len).decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/api/health":
                engine = SautiMeshEngine(db_path=db_path)
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "service": "sautimesh",
                        "version": __version__,
                        "metrics": engine.store.summary_metrics(),
                    },
                )
                return
            if path == "/api/eval":
                self._send_json(200, run_benchmark_suite())
                return
            if path == "/api/queue":
                engine = SautiMeshEngine(db_path=db_path)
                self._send_json(
                    200,
                    {
                        "metrics": engine.store.summary_metrics(),
                        "items": engine.store.list_outbox(limit=50),
                    },
                )
                return
            if path == "/api/dpg":
                self._send_json(200, generate_dpg_transparency_card())
                return

            self._serve_static(path)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            body = self._read_json_body()
            if path == "/api/analyze":
                text = str(body.get("text", "")).strip()
                if not text:
                    self._send_json(400, {"error": "Field 'text' is required."})
                    return
                hint = body.get("hint_language")
                res = analyze_utterance(text, hint_language=str(hint) if hint else None)
                self._send_json(200, res.to_dict())
                return

            if path == "/api/turn":
                text = str(body.get("text", "")).strip()
                if not text:
                    self._send_json(400, {"error": "Field 'text' is required."})
                    return
                cfg = CascadeConfig(
                    offline_mode=bool(body.get("offline_mode", True)),
                    currency_code=str(body.get("currency_code", "UGX")),
                )
                engine = SautiMeshEngine(db_path=db_path, cascade_config=cfg)
                turn = engine.run_turn(
                    text=text,
                    channel=str(body.get("channel", "voice")),
                    hint_language=body.get("hint_language"),
                )
                self._send_json(200, turn.to_dict())
                return

            if path == "/api/sync":
                engine = SautiMeshEngine(db_path=db_path)
                self._send_json(200, engine.store.sync_outbox())
                return

            self._send_json(404, {"error": f"Unknown API endpoint: {path}"})

        def _serve_static(self, req_path: str) -> None:
            if static_dir is None or not static_dir.exists():
                self._send_json(200, {"service": "sautimesh", "docs": "/api/health"})
                return
            rel = "index.html" if req_path in {"", "/"} else req_path.lstrip("/")
            candidate = (static_dir / rel).resolve()
            root = static_dir.resolve()
            if root not in candidate.parents and candidate != root:
                self._send_json(403, {"error": "Forbidden path."})
                return
            if candidate.is_dir():
                candidate = candidate / "index.html"
            if not candidate.exists():
                self._send_json(404, {"error": "File not found."})
                return
            mime, _ = mimetypes.guess_type(str(candidate))
            data = candidate.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return SautiMeshRequestHandler


def run_web_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    db_path: str | Path = ".sautimesh/sautimesh.db",
    static_dir: str | Path | None = None,
) -> ThreadingHTTPServer:
    """Create and return configured ThreadingHTTPServer instance."""
    resolved_static = Path(static_dir) if static_dir else Path(__file__).resolve().parent.parent / "website"
    handler = create_handler(db_path=Path(db_path), static_dir=resolved_static)
    return ThreadingHTTPServer((host, port), handler)
