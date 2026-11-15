"""Tests for MCP server, HTTP workbench API, and CLI commands."""

from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path

from sautimesh.cli import main
from sautimesh.mcp_server import handle_mcp_request
from sautimesh.web_server import run_web_server


def test_mcp_protocol_and_tools(tmp_path: Path) -> None:
    db = tmp_path / "mcp.db"
    init_resp = handle_mcp_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"}, db_path=db)
    assert init_resp is not None
    assert init_resp["result"]["serverInfo"]["name"] == "sautimesh"

    list_resp = handle_mcp_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, db_path=db)
    assert len(list_resp["result"]["tools"]) == 5

    call_resp = handle_mcp_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "sautimesh_analyze_utterance",
                "arguments": {"text": "Sannu malam, kwari suna cin masara a gona"},
            },
        },
        db_path=db,
    )
    payload = json.loads(call_resp["result"]["content"][0]["text"])
    assert "ha" in payload["detected_languages"]
    assert payload["domain"] == "agri_extension"


def test_web_server_endpoints(tmp_path: Path) -> None:
    db = tmp_path / "web.db"
    server = run_web_server(host="127.0.0.1", port=0, db_path=db, static_dir=tmp_path)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3.0) as resp:
            assert resp.status == 200
            health = json.loads(resp.read().decode("utf-8"))
            assert health["service"] == "sautimesh"

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/turn",
            data=json.dumps({"text": "Habari mtoto ana fever", "currency_code": "KES"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            assert resp.status == 200
            turn = json.loads(resp.read().decode("utf-8"))
            assert turn["decision"]["currency_code"] == "KES"
            assert turn["decision"]["offline_contained"] is True
    finally:
        server.shutdown()
        server.server_close()


def test_cli_eval_doctor_and_dpg_card(tmp_path: Path, capsys) -> None:
    db = str(tmp_path / "cli.db")
    assert main(["--db", db, "eval"]) == 0
    out_eval = json.loads(capsys.readouterr().out)
    assert out_eval["pass_rate_pct"] == 100.0

    assert main(["--db", db, "doctor"]) == 0
    out_doc = json.loads(capsys.readouterr().out)
    assert "lg" in out_doc["supported_languages"]

    assert main(["--db", db, "dpg-card", "--format", "json"]) == 0
    out_dpg = json.loads(capsys.readouterr().out)
    assert out_dpg["schema"] == "sautimesh.dpg.v1"
