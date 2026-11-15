"""Tests for 16 kHz PCM WAV synthesis, VAD detection, and ASR/TTS adapters."""

from __future__ import annotations

from pathlib import Path

from sautimesh.audio import analyze_wav, synthesize_tone_wav
from sautimesh.speech import (
    OfflineAcousticFallbackASR,
    OfflineCadenceTTS,
    format_for_voice_and_channels,
)


def test_wav_synthesis_and_vad_telemetry(tmp_path: Path) -> None:
    wav_path = synthesize_tone_wav(tmp_path / "sample.wav", "Habari mtoto ana fever")
    assert wav_path.exists()
    stats = analyze_wav(wav_path)
    assert stats.sample_rate_hz == 16000
    assert stats.channels == 1
    assert stats.duration_ms > 200
    assert len(stats.speech_segments) >= 1
    assert stats.compressed_opus_bytes > 0
    assert stats.compressed_opus_bytes < stats.raw_wav_bytes


def test_offline_sidecar_asr_and_tts_formatting(tmp_path: Path) -> None:
    wav_path = tmp_path / "field_clip.wav"
    synthesize_tone_wav(wav_path, "test clip")
    wav_path.with_suffix(".txt").write_text("Habari mtoto ana homa leo", encoding="utf-8")

    asr = OfflineAcousticFallbackASR()
    transcript, conf = asr.transcribe(wav_path, hint_language="sw")
    assert transcript == "Habari mtoto ana homa leo"
    assert conf > 0.8

    tts = OfflineCadenceTTS()
    out = tts.synthesize("Mpeleke kliniki haraka.", tmp_path / "reply.wav", language="sw")
    assert out.exists()

    spoken, sms, ussd = format_for_voice_and_channels("**Reply:** Visit `clinic` now.")
    assert "*" not in spoken and "`" not in spoken
    assert len(sms) <= 160
    assert ussd.startswith("END ")
