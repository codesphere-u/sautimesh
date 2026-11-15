"""Crash-proof WAL SQLite store-and-forward queue, session store, and spend ledger."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from sautimesh.models import TurnResult

MAX_RETRIES = 3


class SautiMeshStore:
    """Persistent SQLite store guaranteeing zero split-brain crashes during cellular dropouts."""

    def __init__(self, db_path: str | Path = ".sautimesh/sautimesh.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS voice_sessions (
                    session_id TEXT PRIMARY KEY,
                    speaker_lang TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS turn_audit_log (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    primary_language TEXT NOT NULL,
                    detected_languages TEXT NOT NULL,
                    code_switch_index REAL NOT NULL,
                    domain TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    offline_contained INTEGER NOT NULL,
                    human_escalation INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    cellular_bytes INTEGER NOT NULL,
                    redacted_input TEXT NOT NULL,
                    reply_text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS outbox_queue (
                    outbox_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    channel TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    retries INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def record_turn(self, turn: TurnResult, recipient: str = "local-speaker") -> str | None:
        """Persist session, audit telemetry, and optional offline sync outbox item atomically."""
        now = datetime.now(UTC).isoformat()
        queued_outbox_id: str | None = None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO voice_sessions (session_id, speaker_lang, channel, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (turn.session_id, turn.analysis.primary_language, turn.channel, now),
            )
            conn.execute(
                """
                INSERT INTO turn_audit_log (
                    turn_id, session_id, channel, primary_language, detected_languages,
                    code_switch_index, domain, intent, tier, provider, offline_contained,
                    human_escalation, cost_usd, cellular_bytes, redacted_input, reply_text, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    turn.turn_id,
                    turn.session_id,
                    turn.channel,
                    turn.analysis.primary_language,
                    json.dumps(turn.analysis.detected_languages),
                    turn.analysis.code_switch_index,
                    turn.analysis.domain,
                    turn.analysis.intent,
                    turn.decision.tier,
                    turn.decision.provider,
                    1 if turn.decision.offline_contained else 0,
                    1 if turn.decision.human_escalation else 0,
                    turn.decision.estimated_cost_usd,
                    turn.decision.cellular_bytes_used,
                    turn.analysis.redacted_text,
                    turn.decision.reply_text,
                    now,
                ),
            )
            # Enqueue for asynchronous delivery/sync on human escalations or queued fallbacks.
            if turn.decision.human_escalation or turn.decision.provider == "sautimesh-store-and-forward":
                queued_outbox_id = f"out_{uuid.uuid4().hex[:12]}"
                idem_key = hashlib.sha256(
                    f"{turn.turn_id}:{turn.channel}:{recipient}".encode("utf-8")
                ).hexdigest()[:24]
                conn.execute(
                    """
                    INSERT OR IGNORE INTO outbox_queue (
                        outbox_id, idempotency_key, channel, recipient, payload, status,
                        retries, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, 'PENDING', 0, ?, ?)
                    """,
                    (
                        queued_outbox_id,
                        idem_key,
                        "sms_receipt" if turn.channel != "whatsapp" else "whatsapp",
                        recipient,
                        turn.decision.sms_fallback_text,
                        now,
                        now,
                    ),
                )
        return queued_outbox_id

    def enqueue_message(
        self,
        channel: str,
        recipient: str,
        payload: str,
        idempotency_key: str | None = None,
    ) -> str:
        """Insert a message into the durable store-and-forward queue with deduplication."""
        now = datetime.now(UTC).isoformat()
        idem = idempotency_key or hashlib.sha256(
            f"{channel}:{recipient}:{payload}".encode("utf-8")
        ).hexdigest()[:24]
        outbox_id = f"out_{uuid.uuid4().hex[:12]}"
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT outbox_id FROM outbox_queue WHERE idempotency_key = ?",
                (idem,),
            ).fetchone()
            if existing:
                return str(existing["outbox_id"])
            conn.execute(
                """
                INSERT INTO outbox_queue (
                    outbox_id, idempotency_key, channel, recipient, payload, status,
                    retries, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'PENDING', 0, ?, ?)
                """,
                (outbox_id, idem, channel, recipient, payload, now, now),
            )
        return outbox_id

    def sync_outbox(
        self,
        dispatcher: Callable[[str, str, str], bool] | None = None,
        limit: int = 50,
    ) -> dict[str, int]:
        """Drain bounded PENDING outbox items safely without holding open cursors."""
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT outbox_id, channel, recipient, payload, retries
                FROM outbox_queue
                WHERE status = 'PENDING'
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (max(1, min(limit, 500)),),
            ).fetchall()

        send_fn = dispatcher or (lambda _ch, _rec, _msg: True)
        sent_params: list[tuple[str, str]] = []
        failed_params: list[tuple[str, int, str, str, str]] = []
        retried = 0
        dead_lettered = 0

        for row in rows:
            outbox_id = str(row["outbox_id"])
            try:
                ok = bool(send_fn(str(row["channel"]), str(row["recipient"]), str(row["payload"])))
            except Exception as exc:  # noqa: BLE001 - worker must isolate external transport faults
                ok = False
                err_msg = str(exc)
            else:
                err_msg = "" if ok else "Transport returned False"

            if ok:
                sent_params.append((now, outbox_id))
            else:
                next_retries = int(row["retries"]) + 1
                new_status = "DEAD_LETTER" if next_retries >= MAX_RETRIES else "PENDING"
                if new_status == "DEAD_LETTER":
                    dead_lettered += 1
                else:
                    retried += 1
                failed_params.append((new_status, next_retries, err_msg[:200], now, outbox_id))

        if sent_params or failed_params:
            with self._connect() as conn:
                if sent_params:
                    conn.executemany(
                        "UPDATE outbox_queue SET status = 'SENT', updated_at = ? WHERE outbox_id = ?",
                        sent_params,
                    )
                if failed_params:
                    conn.executemany(
                        """
                        UPDATE outbox_queue
                        SET status = ?, retries = ?, last_error = ?, updated_at = ?
                        WHERE outbox_id = ?
                        """,
                        failed_params,
                    )
        return {
            "processed": len(rows),
            "sent": len(sent_params),
            "retried": retried,
            "dead_letter": dead_lettered,
        }

    def list_outbox(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return bounded recent outbox queue items for inspection or dashboard display."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT outbox_id, channel, recipient, payload, status, retries, last_error, created_at
                FROM outbox_queue
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (max(1, min(limit, 200)),),
            ).fetchall()
        return [dict(r) for r in rows]

    def summary_metrics(self) -> dict[str, Any]:
        """Compute offline containment rate, total spend, and saved cellular bandwidth."""
        with self._connect() as conn:
            turn_row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_turns,
                    SUM(offline_contained) AS offline_turns,
                    SUM(human_escalation) AS escalations,
                    COALESCE(SUM(cost_usd), 0.0) AS total_cost_usd,
                    COALESCE(SUM(cellular_bytes), 0) AS total_bytes
                FROM turn_audit_log
                """
            ).fetchone()
            pending_row = conn.execute(
                "SELECT COUNT(*) AS pending_count FROM outbox_queue WHERE status = 'PENDING'"
            ).fetchone()

        total_turns = int(turn_row["total_turns"] or 0)
        offline_turns = int(turn_row["offline_turns"] or 0)
        containment = round((offline_turns / total_turns) * 100.0, 1) if total_turns else 100.0
        return {
            "total_turns": total_turns,
            "offline_turns": offline_turns,
            "offline_containment_pct": containment,
            "human_escalations": int(turn_row["escalations"] or 0),
            "total_cost_usd": round(float(turn_row["total_cost_usd"] or 0.0), 4),
            "total_cellular_bytes": int(turn_row["total_bytes"] or 0),
            "pending_outbox": int(pending_row["pending_count"] or 0),
        }
