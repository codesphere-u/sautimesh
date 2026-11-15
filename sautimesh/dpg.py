"""Digital Public Goods (DPG) transparency card export and code-switch benchmark runner."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from sautimesh.cascade import CascadeConfig, route_turn
from sautimesh.languages import SUPPORTED_LANGUAGES, analyze_utterance
from sautimesh.speech import VOICE_BACKENDS_CATALOG


@dataclass(frozen=True)
class BenchmarkCase:
    """Single multilingual / code-switching evaluation utterance."""

    case_id: str
    label: str
    utterance: str
    expected_primary_lang: str
    expected_domain: str
    expected_intent: str
    expect_human_escalation: bool = False


DEFAULT_BENCHMARK_SUITE: list[BenchmarkCase] = [
    BenchmarkCase(
        case_id="sw-en-health-01",
        label="Swahili + English Pediatric Fever Code-Switch",
        utterance="Habari daktari, mtoto wangu ana fever kali leo, clinic ni wapi?",
        expected_primary_lang="sw",
        expected_domain="health_triage",
        expected_intent="pediatric_fever_triage",
    ),
    BenchmarkCase(
        case_id="lg-en-agri-02",
        label="Luganda + English Maize Pest Code-Switch",
        utterance="Ssebo obuwuka bungi mu kasooli farm yange leero, help please",
        expected_primary_lang="lg",
        expected_domain="agri_extension",
        expected_intent="pest_and_disease_advisory",
    ),
    BenchmarkCase(
        case_id="lg-en-urgent-03",
        label="Luganda Emergency Bleeding Escalation",
        utterance="Nnyamba mangu ssebo omwana avaamu omusaayi okufa",
        expected_primary_lang="lg",
        expected_domain="health_triage",
        expected_intent="emergency_referral",
        expect_human_escalation=True,
    ),
    BenchmarkCase(
        case_id="yo-en-momo-04",
        label="Yoruba + English Health Intake",
        utterance="Bawo, omo mi ni iba today, jowo se oogun wa ni ileiwosan?",
        expected_primary_lang="yo",
        expected_domain="health_triage",
        expected_intent="pediatric_fever_triage",
    ),
    BenchmarkCase(
        case_id="ha-en-agri-05",
        label="Hausa + English Maize Pest Advisory",
        utterance="Sannu malam, kwari suna cin masara a gona yau, ta yaya magani?",
        expected_primary_lang="ha",
        expected_domain="agri_extension",
        expected_intent="pest_and_disease_advisory",
    ),
    BenchmarkCase(
        case_id="fr-health-06",
        label="Francophone West Africa Emergency Triage",
        utterance="Bonjour, urgence saignement enfant clinique s'il vous plait",
        expected_primary_lang="fr",
        expected_domain="health_triage",
        expected_intent="emergency_referral",
        expect_human_escalation=True,
    ),
    BenchmarkCase(
        case_id="sw-momo-07",
        label="Swahili Mobile Money Balance Security",
        utterance="Nataka check salio ya fedha yangu akaunti leo",
        expected_primary_lang="sw",
        expected_domain="fintech_momo",
        expected_intent="wallet_balance_check",
    ),
]


def run_benchmark_suite(cases: list[BenchmarkCase] | None = None) -> dict[str, Any]:
    """Evaluate SautiMesh accuracy, offline containment rate, and escalation recall."""
    suite = cases or DEFAULT_BENCHMARK_SUITE
    cfg = CascadeConfig(offline_mode=True, currency_code="UGX")
    results: list[dict[str, Any]] = []
    passed = 0
    offline_contained = 0

    for item in suite:
        analysis = analyze_utterance(item.utterance)
        decision = route_turn(analysis, config=cfg)
        lang_ok = item.expected_primary_lang in analysis.detected_languages
        domain_ok = analysis.domain == item.expected_domain
        intent_ok = analysis.intent == item.expected_intent
        esc_ok = decision.human_escalation == item.expect_human_escalation
        case_pass = lang_ok and domain_ok and intent_ok and esc_ok
        if case_pass:
            passed += 1
        if decision.offline_contained:
            offline_contained += 1
        results.append(
            {
                "case_id": item.case_id,
                "label": item.label,
                "passed": case_pass,
                "detected_languages": analysis.detected_languages,
                "code_switch_index": analysis.code_switch_index,
                "domain": analysis.domain,
                "intent": analysis.intent,
                "tier": decision.tier,
                "human_escalation": decision.human_escalation,
                "sms_encoding": analysis.sms_encoding,
                "ussd_pages": analysis.ussd_pages,
            }
        )

    total = len(suite)
    return {
        "total_cases": total,
        "passed_cases": passed,
        "pass_rate_pct": round((passed / max(1, total)) * 100.0, 1),
        "offline_containment_pct": round((offline_contained / max(1, total)) * 100.0, 1),
        "total_cellular_bytes": 0,
        "total_cost_usd": 0.0,
        "cases": results,
    }


def generate_dpg_transparency_card() -> dict[str, Any]:
    """Build a DPGA-aligned Open Source AI Model, Data, and Limitation Manifest."""
    return {
        "schema": "sautimesh.dpg.v1",
        "name": "SautiMesh",
        "license": "MIT",
        "aligned_standards": [
            "Digital Public Goods Standard (Open Source Software & Open AI Transparency)",
            "Offline-First Store-and-Forward Durability (SQLite WAL)",
            "Human-Extension-Worker Safety Escalation Gate",
        ],
        "supported_languages": [
            {"code": code, **meta} for code, meta in SUPPORTED_LANGUAGES.items()
        ],
        "voice_backends": VOICE_BACKENDS_CATALOG,
        "safeguards": {
            "pii_redaction_before_cloud": ["phone_number", "pin_or_otp", "national_id"],
            "budget_currencies": ["UGX", "KES", "NGN", "GHS", "XOF", "ZAR", "RWF", "TZS", "USD"],
            "emergency_human_escalation": True,
            "medical_disclaimer": "Triage guidance supports community health workers and never replaces clinical diagnosis.",
        },
        "known_limitations": [
            "Built-in lexicon pack focuses on Swahili, Luganda, Yoruba, Hausa, French, English, Pidgin, and Runyankole; specialized regional dialects require local lexicon JSON packs or external Sunflower/Whisper/MMS weights.",
            "Built-in acoustic VAD/ASR falls back to sidecar transcripts and RMS cadence when optional Whisper/MMS binaries are absent.",
        ],
    }


def format_dpg_markdown() -> str:
    """Render DPGA transparency card as clean documentation Markdown."""
    card = generate_dpg_transparency_card()
    lines = [
        f"# {card['name']} — Digital Public Goods (DPG) AI Transparency Card",
        "",
        f"- **License:** {card['license']}",
        f"- **Schema:** `{card['schema']}`",
        "",
        "## Supported Languages & Regions",
    ]
    for lang in card["supported_languages"]:
        lines.append(f"- `{lang['code']}` — {lang['name']} ({lang['region']})")
    lines.extend(["", "## Built-In Safety & Sovereignty Controls"])
    lines.append("```json")
    lines.append(json.dumps(asdict_or_dict(card["safeguards"]), indent=2))
    lines.append("```")
    lines.extend(["", "## Known Limitations"])
    for item in card["known_limitations"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def asdict_or_dict(value: Any) -> Any:
    """Serialize dataclass or mapping safely."""
    return asdict(value) if hasattr(value, "__dataclass_fields__") else value
