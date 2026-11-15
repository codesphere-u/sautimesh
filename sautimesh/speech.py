"""Pluggable ASR/TTS Speech Registry with zero-dependency offline engines and production CLI adapters."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sautimesh.audio import analyze_wav, synthesize_tone_wav
from sautimesh.languages import detect_sms_encoding


class ASRProvider(Protocol):
    """Protocol implemented by local or remote Speech-to-Text backends."""

    name: str

    def transcribe(self, wav_path: Path, hint_language: str | None = None) -> tuple[str, float]:
        """Return (transcript_text, confidence)."""
        ...


class TTSProvider(Protocol):
    """Protocol implemented by local or remote Text-to-Speech backends."""

    name: str

    def synthesize(self, text: str, output_wav: Path, language: str = "en") -> Path:
        """Synthesize spoken audio into output_wav and return its Path."""
        ...


@dataclass(frozen=True)
class OfflineAcousticFallbackASR:
    """Deterministic fallback ASR used when heavy Whisper/MMS binaries are not installed."""

    name: str = "offline-acoustic-vad"

    def transcribe(self, wav_path: Path, hint_language: str | None = None) -> tuple[str, float]:
        stats = analyze_wav(wav_path)
        lang_tag = hint_language or "sw"
        segment_note = f"{len(stats.speech_segments)} speech span(s), {stats.duration_ms}ms"
        # Sidecar `.txt` transcript allows realistic offline simulation replays from recorded field WAVs.
        sidecar = wav_path.with_suffix(".txt")
        if sidecar.exists():
            text = sidecar.read_text(encoding="utf-8").strip()
            if text:
                return text, 0.91
        return f"[{lang_tag} voice sample detected: {segment_note}] help", 0.55


@dataclass(frozen=True)
class ExternalCommandASR:
    """Subprocess adapter for whisper.cpp, faster-whisper CLI, or sherpa-onnx executables."""

    executable: str = "whisper-cli"
    model_path: str = "models/ggml-base.bin"
    name: str = "whisper-cli"

    def is_available(self) -> bool:
        """Check whether the configured ASR binary and model exist locally."""
        return shutil.which(self.executable) is not None and Path(self.model_path).exists()

    def transcribe(self, wav_path: Path, hint_language: str | None = None) -> tuple[str, float]:
        if not self.is_available():
            return OfflineAcousticFallbackASR().transcribe(wav_path, hint_language=hint_language)
        cmd = [self.executable, "-m", self.model_path, "-f", str(wav_path), "--no-timestamps"]
        if hint_language:
            cmd.extend(["-l", hint_language])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        if proc.returncode != 0 or not proc.stdout.strip():
            return OfflineAcousticFallbackASR().transcribe(wav_path, hint_language=hint_language)
        return proc.stdout.strip(), 0.88


@dataclass(frozen=True)
class OfflineCadenceTTS:
    """Zero-dependency offline PCM synthesizer emitting valid 16 kHz speech-cadence WAVs."""

    name: str = "offline-cadence-pcm"

    def synthesize(self, text: str, output_wav: Path, language: str = "en") -> Path:
        return synthesize_tone_wav(output_wav, text=f"[{language}] {text}")


@dataclass(frozen=True)
class PiperCommandTTS:
    """Subprocess adapter for Piper ONNX TTS or USOAL Luganda/Swahili local voices."""

    executable: str = "piper"
    model_path: str = "voices/sw_CD-lanfrica-medium.onnx"
    name: str = "piper-onnx"

    def is_available(self) -> bool:
        """Return True when Piper CLI and target ONNX voice model are present."""
        return shutil.which(self.executable) is not None and Path(self.model_path).exists()

    def synthesize(self, text: str, output_wav: Path, language: str = "en") -> Path:
        if not self.is_available():
            return OfflineCadenceTTS().synthesize(text, output_wav, language=language)
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(
            [self.executable, "--model", self.model_path, "--output_file", str(output_wav)],
            input=text,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0 or not output_wav.exists():
            return OfflineCadenceTTS().synthesize(text, output_wav, language=language)
        return output_wav


VOICE_BACKENDS_CATALOG: list[dict[str, str]] = [
    {
        "id": "offline-acoustic-vad",
        "kind": "ASR",
        "runtime": "Built-in Pure Python + 16kHz VAD",
        "languages": "All 8 core languages (sidecar + acoustic telemetry)",
    },
    {
        "id": "sunbird-sunflower-v2",
        "kind": "ASR/LLM/TTS",
        "runtime": "Sunbird AI Sunflower v2 (Open Weights / HTTP / Edge GGUF)",
        "languages": "67 African languages incl. Luganda, Swahili, Runyankole",
    },
    {
        "id": "whisper-cpp-mms",
        "kind": "ASR",
        "runtime": "whisper.cpp / faster-whisper / Meta MMS",
        "languages": "Swahili, Yoruba, Hausa, French, English + 99 languages",
    },
    {
        "id": "piper-usoal-tts",
        "kind": "TTS",
        "runtime": "Piper ONNX / USOAL Luganda / Msingi Swahili",
        "languages": "Consented regional voices for offline mobile synthesis",
    },
]


def format_for_voice_and_channels(reply_text: str) -> tuple[str, str, str]:
    """Produce concise spoken text, a single SMS fallback string, and a 182-char USSD summary."""
    # Strip markdown decorators so TTS voices never read literal asterisks or backticks aloud.
    spoken = " ".join(
        reply_text.replace("**", "").replace("`", "").replace("#", "").split()
    )
    encoding, _, _ = detect_sms_encoding(spoken)
    sms_cap = 156 if encoding == "GSM-7" else 67
    ussd_cap = 178 if encoding == "GSM-7" else 76

    sms_fallback = spoken if len(spoken) <= sms_cap else f"{spoken[:sms_cap].rstrip()}..."
    ussd_preview = (
        f"END {spoken}"
        if len(spoken) + 4 <= ussd_cap
        else f"CON {spoken[: max(20, ussd_cap - 18)].rstrip()}..\n98:More"
    )
    return spoken, sms_fallback, ussd_preview
