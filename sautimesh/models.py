"""Typed domain models used across the SautiMesh runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class LanguageSpan:
    """Single token or phrase classified with an ISO-like language tag."""

    token: str
    lang: str
    normalized: str


@dataclass(frozen=True)
class CodeSwitchAnalysis:
    """Token-level multilingual analysis for a spoken or typed utterance."""

    original_text: str
    normalized_text: str
    redacted_text: str
    primary_language: str
    detected_languages: list[str]
    code_switch_index: float
    spans: list[LanguageSpan]
    domain: str
    intent: str
    confidence: float
    urgency: str
    currency_mentions: list[dict[str, Any]]
    sms_encoding: str
    sms_segments: int
    ussd_pages: int
    pii_redacted: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize analysis payload to JSON-friendly dictionary."""
        data = asdict(self)
        data["spans"] = [asdict(s) for s in self.spans]
        return data


@dataclass(frozen=True)
class SpeechInputStats:
    """Acoustic telemetry extracted from a 16-bit PCM WAV utterance."""

    sample_rate_hz: int
    channels: int
    duration_ms: int
    rms_energy: float
    snr_db: float
    speech_segments: list[tuple[int, int]]
    raw_wav_bytes: int
    compressed_opus_bytes: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize audio telemetry to JSON-friendly dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class RouteDecision:
    """Routing decision across offline rules, local SLM, and cloud fallback."""

    tier: str  # 'offline_rules' | 'local_slm' | 'cloud_fallback'
    provider: str
    model: str
    reply_text: str
    reply_language: str
    sms_fallback_text: str
    ussd_preview_text: str
    human_escalation: bool
    escalation_reason: str | None
    latency_ms: float
    estimated_cost_usd: float
    estimated_cost_local: float
    currency_code: str
    cellular_bytes_used: int
    offline_contained: bool
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize route decision to JSON-friendly dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class TurnResult:
    """Complete end-to-end voice agent turn record."""

    turn_id: str
    session_id: str
    channel: str
    analysis: CodeSwitchAnalysis
    decision: RouteDecision
    audio_stats: SpeechInputStats | None = None
    output_wav_path: str | None = None
    queued_outbox_id: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize full turn result to JSON-friendly dictionary."""
        return {
            "turn_id": self.turn_id,
            "session_id": self.session_id,
            "channel": self.channel,
            "analysis": self.analysis.to_dict(),
            "decision": self.decision.to_dict(),
            "audio_stats": self.audio_stats.to_dict() if self.audio_stats else None,
            "output_wav_path": self.output_wav_path,
            "queued_outbox_id": self.queued_outbox_id,
            "warnings": list(self.warnings),
        }
