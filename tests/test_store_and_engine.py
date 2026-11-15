"""Tests for SQLite store-and-forward queue durability, idempotency, and orchestrator."""

from __future__ import annotations

from pathlib import Path

from sautimesh.audio import synthesize_tone_wav
from sautimesh.cascade import CascadeConfig
from sautimesh.dpg import run_benchmark_suite
from sautimesh.engine import SautiMeshEngine


def test_engine_end_to_end_and_outbox_retry_dead_letter(tmp_path: Path) -> None:
    db_file = tmp_path / "mesh.db"
    in_wav = tmp_path / "input.wav"
    synthesize_tone_wav(in_wav, "Luganda urgent help")
    in_wav.with_suffix(".txt").write_text(
        "Nnyamba mangu ssebo omwana avaamu omusaayi", encoding="utf-8"
    )
    out_wav = tmp_path / "reply.wav"

    engine = SautiMeshEngine(
        db_path=db_file,
        cascade_config=CascadeConfig(offline_mode=True, currency_code="UGX"),
    )
    turn = engine.run_turn(
        wav_path=in_wav,
        channel="whatsapp_voice",
        recipient="+256700000001",
        output_wav_path=out_wav,
    )
    assert turn.audio_stats is not None
    assert Path(turn.output_wav_path or "").exists()
    assert turn.queued_outbox_id is not None

    # Deduplicated enqueue with same idempotency key keeps single row.
    id1 = engine.store.enqueue_message("sms", "+256700000002", "Test receipt", idempotency_key="k1")
    id2 = engine.store.enqueue_message("sms", "+256700000002", "Test receipt", idempotency_key="k1")
    assert id1 == id2

    # Three consecutive failures move an outbox item to DEAD_LETTER cleanly.
    for _ in range(3):
        engine.store.sync_outbox(dispatcher=lambda *_args: False)
    rows = engine.store.list_outbox(limit=20)
    assert all(r["status"] == "DEAD_LETTER" for r in rows)


def test_multilingual_benchmark_suite_passes_100_percent() -> None:
    report = run_benchmark_suite()
    assert report["total_cases"] == 7
    assert report["passed_cases"] == 7
    assert report["offline_containment_pct"] == 100.0
    assert report["total_cost_usd"] == 0.0
