"""Tests for multilingual code-switching analysis, PII redaction, GSM/UCS-2 packing, and cascade."""

from __future__ import annotations

from sautimesh.cascade import CascadeConfig, route_turn
from sautimesh.languages import analyze_utterance, detect_sms_encoding


def test_swahili_english_code_switch_and_pii_redaction() -> None:
    text = "Habari daktari, mtoto ana fever kali leo PIN: 4829 call +256701234567"
    analysis = analyze_utterance(text)
    assert "sw" in analysis.detected_languages
    assert "en" in analysis.detected_languages
    assert analysis.code_switch_index > 0.0
    assert analysis.domain == "health_triage"
    assert analysis.intent == "pediatric_fever_triage"
    assert "pin_or_otp" in analysis.pii_redacted
    assert "phone_number" in analysis.pii_redacted
    assert "4829" not in analysis.redacted_text
    assert "256701234567" not in analysis.redacted_text


def test_luganda_emergency_escalation_and_sms_encoding() -> None:
    text = "Nnyamba mangu ssebo omwana avaamu omusaayi okufa"
    analysis = analyze_utterance(text)
    assert analysis.primary_language == "lg"
    assert analysis.urgency == "high"

    decision = route_turn(analysis, config=CascadeConfig(offline_mode=True, currency_code="UGX"))
    assert decision.offline_contained is True
    assert decision.human_escalation is True
    assert decision.estimated_cost_usd == 0.0
    assert decision.cellular_bytes_used == 0

    enc, sms_segs, ussd_pages = detect_sms_encoding("Ọmọ mi ní ibà lónìí ṣé oògùn wà")
    assert enc == "UCS-2"
    assert sms_segs == 1
    assert ussd_pages == 1


def test_budget_cap_blocks_cloud_fallback_when_exhausted() -> None:
    analysis = analyze_utterance("Explain cooperative grain storage contracts in detail")
    calls = {"cloud": 0}

    def fake_transport(endpoint: str, model: str, prompt: str, timeout: float, api_key: str | None):
        calls["cloud"] += 1
        return "Cloud reply"

    decision = route_turn(
        analysis,
        config=CascadeConfig(
            offline_mode=False,
            local_slm_url="",
            cloud_url="https://api.example.invalid/v1/chat/completions",
            daily_budget_usd=0.001,
            spent_today_usd=0.001,
            currency_code="KES",
        ),
        transport_fn=fake_transport,
    )
    assert calls["cloud"] == 0
    assert decision.offline_contained is True
    assert decision.provider == "sautimesh-store-and-forward"
    assert decision.currency_code == "KES"
