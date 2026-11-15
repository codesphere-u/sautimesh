"""High-level SautiMesh turn orchestrator combining audio, code-switch analysis, cascade, and SQLite."""

from __future__ import annotations

import uuid
from pathlib import Path

from sautimesh.audio import analyze_wav
from sautimesh.cascade import CascadeConfig, route_turn
from sautimesh.languages import analyze_utterance
from sautimesh.models import SpeechInputStats, TurnResult
from sautimesh.speech import (
    ASRProvider,
    OfflineAcousticFallbackASR,
    OfflineCadenceTTS,
    TTSProvider,
)
from sautimesh.store import SautiMeshStore


class SautiMeshEngine:
    """Cohesive voice-first multilingual agent runtime with durable offline queue."""

    def __init__(
        self,
        db_path: str | Path = ".sautimesh/sautimesh.db",
        cascade_config: CascadeConfig | None = None,
        asr: ASRProvider | None = None,
        tts: TTSProvider | None = None,
    ) -> None:
        self.store = SautiMeshStore(db_path=db_path)
        self.config = cascade_config or CascadeConfig()
        self.asr: ASRProvider = asr or OfflineAcousticFallbackASR()
        self.tts: TTSProvider = tts or OfflineCadenceTTS()

    def run_turn(
        self,
        text: str | None = None,
        wav_path: str | Path | None = None,
        channel: str = "voice",
        session_id: str | None = None,
        hint_language: str | None = None,
        recipient: str = "local-speaker",
        output_wav_path: str | Path | None = None,
    ) -> TurnResult:
        """Process one voice/text turn end-to-end and persist durability telemetry."""
        if not text and not wav_path:
            raise ValueError("Provide either text or wav_path for a SautiMesh turn.")

        audio_stats: SpeechInputStats | None = None
        warnings: list[str] = []
        utterance = (text or "").strip()

        if wav_path is not None:
            wav_file = Path(wav_path)
            audio_stats = analyze_wav(wav_file)
            if audio_stats.snr_db < 6.0 and audio_stats.duration_ms > 0:
                warnings.append(f"Low acoustic SNR ({audio_stats.snr_db} dB); background noise high.")
            if not utterance:
                utterance, _asr_conf = self.asr.transcribe(wav_file, hint_language=hint_language)

        analysis = analyze_utterance(utterance, hint_language=hint_language)
        summary = self.store.summary_metrics()
        active_cfg = CascadeConfig(
            offline_mode=self.config.offline_mode,
            local_slm_url=self.config.local_slm_url,
            local_slm_model=self.config.local_slm_model,
            cloud_url=self.config.cloud_url,
            cloud_model=self.config.cloud_model,
            cloud_api_key=self.config.cloud_api_key,
            min_confidence_for_offline=self.config.min_confidence_for_offline,
            currency_code=self.config.currency_code,
            daily_budget_usd=self.config.daily_budget_usd,
            spent_today_usd=float(summary["total_cost_usd"]),
            http_timeout_s=self.config.http_timeout_s,
        )
        decision = route_turn(analysis, config=active_cfg)

        synthesized_path: str | None = None
        if output_wav_path is not None:
            rendered = self.tts.synthesize(
                decision.reply_text,
                Path(output_wav_path),
                language=decision.reply_language,
            )
            synthesized_path = str(rendered)

        turn_id = f"turn_{uuid.uuid4().hex[:12]}"
        sess_id = session_id or f"sess_{uuid.uuid4().hex[:10]}"
        pending_turn = TurnResult(
            turn_id=turn_id,
            session_id=sess_id,
            channel=channel,
            analysis=analysis,
            decision=decision,
            audio_stats=audio_stats,
            output_wav_path=synthesized_path,
            queued_outbox_id=None,
            warnings=warnings,
        )
        outbox_id = self.store.record_turn(pending_turn, recipient=recipient)
        return TurnResult(
            turn_id=turn_id,
            session_id=sess_id,
            channel=channel,
            analysis=analysis,
            decision=decision,
            audio_stats=audio_stats,
            output_wav_path=synthesized_path,
            queued_outbox_id=outbox_id,
            warnings=warnings,
        )
