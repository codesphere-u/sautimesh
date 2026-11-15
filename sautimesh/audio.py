"""Pure-Python 16 kHz PCM WAV processing, lightweight VAD, and data-cost estimation."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from sautimesh.models import SpeechInputStats

DEFAULT_SAMPLE_RATE = 16000
FRAME_MS = 30
OPUS_BITRATE_BPS = 16000


def synthesize_tone_wav(
    path: str | Path,
    text: str,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> Path:
    """Synthesize a deterministic speech-cadence PCM WAV file without external TTS weights.

    Why: Allows offline unit tests, Termux edge probes, and UI waveform previews to work cleanly
    on any Python installation even when optional Piper/USOAL voice weights are not installed.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    words = [w for w in text.strip().split() if w]
    syllable_count = max(3, min(40, sum(max(1, len(w) // 3) for w in words)))
    frames: list[bytes] = []
    silence_len = int(sample_rate * 0.045)
    silence_chunk = struct.pack("<" + "h" * silence_len, *([0] * silence_len))

    for idx in range(syllable_count):
        freq = 165.0 + ((idx * 37 + len(text)) % 140)
        tone_samples = int(sample_rate * 0.085)
        pcm = []
        for s in range(tone_samples):
            envelope = math.sin(math.pi * s / tone_samples)
            val = int(12000 * envelope * math.sin(2.0 * math.pi * freq * s / sample_rate))
            pcm.append(val)
        frames.append(struct.pack("<" + "h" * tone_samples, *pcm))
        frames.append(silence_chunk)

    with wave.open(str(target), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))
    return target


def read_wav_pcm16(path: str | Path) -> tuple[int, int, list[int]]:
    """Read a WAV file and return (sample_rate, channels, mono 16-bit integer samples)."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    with wave.open(str(file_path), "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        frame_count = wf.getnframes()
        raw = wf.readframes(frame_count)

    if sample_width != 2:
        raise ValueError(f"Expected 16-bit PCM WAV (sampwidth=2), got sampwidth={sample_width}")
    total_samples = len(raw) // 2
    samples = list(struct.unpack("<" + "h" * total_samples, raw))
    if channels > 1:
        mono = [
            sum(samples[i : i + channels]) // channels
            for i in range(0, len(samples), channels)
        ]
        return sample_rate, channels, mono
    return sample_rate, channels, samples


def detect_speech_segments(
    samples: list[int],
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    energy_threshold: float = 420.0,
) -> list[tuple[int, int]]:
    """Detect active speech spans in milliseconds using frame RMS energy + ZCR gating."""
    if not samples or sample_rate <= 0:
        return []
    frame_len = max(1, int(sample_rate * (FRAME_MS / 1000.0)))
    segments: list[tuple[int, int]] = []
    active_start_ms: int | None = None
    trailing_silent_frames = 0

    for idx in range(0, len(samples), frame_len):
        chunk = samples[idx : idx + frame_len]
        if not chunk:
            continue
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))
        crossings = sum(
            1 for a, b in zip(chunk, chunk[1:]) if (a >= 0 > b) or (a < 0 <= b)
        )
        zcr = crossings / max(1, len(chunk))
        current_ms = int((idx / sample_rate) * 1000)
        is_voice = rms >= energy_threshold and 0.005 <= zcr <= 0.45

        if is_voice:
            if active_start_ms is None:
                active_start_ms = current_ms
            trailing_silent_frames = 0
        elif active_start_ms is not None:
            trailing_silent_frames += 1
            if trailing_silent_frames >= 3:
                end_ms = int(((idx + len(chunk)) / sample_rate) * 1000)
                segments.append((active_start_ms, end_ms))
                active_start_ms = None
                trailing_silent_frames = 0

    if active_start_ms is not None:
        end_ms = int((len(samples) / sample_rate) * 1000)
        segments.append((active_start_ms, end_ms))
    return segments


def analyze_wav(path: str | Path) -> SpeechInputStats:
    """Inspect a WAV file for VAD segments, noise SNR, and cellular Opus data estimate."""
    file_path = Path(path)
    raw_wav_bytes = file_path.stat().st_size
    sample_rate, channels, samples = read_wav_pcm16(file_path)
    duration_ms = int((len(samples) / max(1, sample_rate)) * 1000)

    if not samples:
        return SpeechInputStats(
            sample_rate_hz=sample_rate,
            channels=channels,
            duration_ms=0,
            rms_energy=0.0,
            snr_db=0.0,
            speech_segments=[],
            raw_wav_bytes=raw_wav_bytes,
            compressed_opus_bytes=0,
        )

    rms = math.sqrt(sum(s * s for s in samples) / len(samples))
    frame_len = max(1, int(sample_rate * (FRAME_MS / 1000.0)))
    frame_rms = [
        math.sqrt(sum(s * s for s in samples[i : i + frame_len]) / len(samples[i : i + frame_len]))
        for i in range(0, len(samples), frame_len)
    ]
    sorted_rms = sorted(frame_rms)
    noise_floor = max(1.0, sorted_rms[max(0, len(sorted_rms) // 5)])
    peak_signal = max(noise_floor, sorted_rms[int(len(sorted_rms) * 0.9)])
    snr_db = round(20.0 * math.log10(peak_signal / noise_floor), 2)

    segments = detect_speech_segments(samples, sample_rate=sample_rate)
    compressed_opus_bytes = int((duration_ms / 1000.0) * (OPUS_BITRATE_BPS / 8.0))

    return SpeechInputStats(
        sample_rate_hz=sample_rate,
        channels=channels,
        duration_ms=duration_ms,
        rms_energy=round(rms, 2),
        snr_db=snr_db,
        speech_segments=segments,
        raw_wav_bytes=raw_wav_bytes,
        compressed_opus_bytes=compressed_opus_bytes,
    )
