"""Tests for Acholi/Kinyarwanda code-switching support and WER/CER evaluation harness."""

from __future__ import annotations

import pytest

from sautimesh.eval_wer import (
    char_error_rate,
    evaluate_asr_benchmark,
    evaluate_asr_sample,
    word_error_rate,
)
from sautimesh.languages import SUPPORTED_LANGUAGES, analyze_utterance


def test_acholi_and_kinyarwanda_code_switching_analysis() -> None:
    assert "ach" in SUPPORTED_LANGUAGES
    assert "rw" in SUPPORTED_LANGUAGES

    ach_res = analyze_utterance("Apwoyo, latin lyeto urgent clinic help")
    assert "ach" in ach_res.detected_languages
    assert ach_res.domain == "health_triage"
    assert ach_res.urgency == "high"

    rw_res = analyze_utterance("Muraho, nshaka ohereza amafaranga mobile money balance")
    assert "rw" in rw_res.detected_languages
    assert rw_res.domain == "fintech_momo"


def test_wer_cer_and_benchmark_summary() -> None:
    assert word_error_rate("Habari mtoto ana homa", "Habari mtoto ana homa") == 0.0
    assert char_error_rate("Habari", "Habari") == 0.0
    assert word_error_rate("one two three four", "one two five four") == 0.25

    sample = evaluate_asr_sample(
        "Oli otya, omwana alina omusujja urgent",
        "Oli otya omwana alina omusujja urgent",
    )
    assert sample.wer == 0.0
    assert sample.language_recall == 1.0
    assert sample.domain_match is True

    summary = evaluate_asr_benchmark(
        [
            ("Habari mtoto homa clinic", "Habari mtoto homa clinic"),
            ("Apwoyo latin lyeto clinic", "Apwoyo latin lyeto hospital"),
        ]
    )
    assert summary.sample_count == 2
    assert summary.mean_wer == 0.125
    assert summary.domain_accuracy == 1.0

    with pytest.raises(ValueError):
        evaluate_asr_benchmark([])
