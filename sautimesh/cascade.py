"""Edge-first model cascade with offline workflow containment, currency budget cap, and PII guard."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from sautimesh.models import CodeSwitchAnalysis, RouteDecision
from sautimesh.speech import format_for_voice_and_channels

EXCHANGE_RATES_PER_USD: dict[str, float] = {
    "USD": 1.0,
    "UGX": 3700.0,
    "KES": 129.0,
    "NGN": 1600.0,
    "GHS": 15.8,
    "XOF": 605.0,
    "ZAR": 18.2,
    "RWF": 1350.0,
    "TZS": 2650.0,
}

OFFLINE_PLAYBOOKS: dict[tuple[str, str], dict[str, dict[str, str]]] = {
    ("health_triage", "emergency_referral"): {
        "sw": {
            "reply": "Hatari kubwa: Tafadhali mpeleke mgonjwa kliniki au hospitali iliyo karibu haraka sana. Mhudumu wa afya amearifiwa.",
        },
        "lg": {
            "reply": "Obulabe obw'amangu: Twala omulwadde mu eddwaliro erisinga okubeera okumpi mangu ddala. Omusawo wa kyalo ategeddeko.",
        },
        "yo": {
            "reply": "Ipajawiri ni eyi: Jowo gbe alaisan lo si ile-iwosan ti o sunmo kiakia. Oluranlowo ilera ti gba ifiranṣẹ.",
        },
        "ha": {
            "reply": "Gaggawa ne: Don Allah ku garzaya da mara lafiya zuwa asibiti mafi kusa nan take. An sanar da ma'aikacin lafiya.",
        },
        "fr": {
            "reply": "Urgence medicale detectee: veuillez conduire le patient a la clinique la plus proche immediatement. Un agent de sante est alerte.",
        },
        "en": {
            "reply": "Urgent alert: Please take the patient to the nearest clinic or health post immediately. A local health worker has been flagged.",
        },
    },
    ("health_triage", "pediatric_fever_triage"): {
        "sw": {
            "reply": "Kwa homa ya mtoto, mpime joto leo, mpe maji mengi safi, na umpeleke kliniki kupima malaria kabla ya kumeza dawa yoyote.",
        },
        "lg": {
            "reply": "Ku musujja gw'omwana, mupime ebbugumu leero, muwe amazzi amayonjo agamala, era omutwale mu eddwaliro bakebere omusujja gw'ensiri.",
        },
        "yo": {
            "reply": "Fun iba omo, se ayewo igbona ara oni, fun ni omi mimu to peye, ki o si mu u lo si ile-iwosan fun ayewo iba.",
        },
        "ha": {
            "reply": "Game da zazzabin yaro, a duba zafin jiki yau, a ba shi ruwa mai tsafta, a kai shi asibiti don gwajin zazzabin cizon sauro.",
        },
        "fr": {
            "reply": "Pour la fievre de l'enfant, surveillez la temperature, hydratez regulierement et consultez un centre de sante pour un test paludisme.",
        },
        "en": {
            "reply": "For child fever triage, check temperature today, give clean fluids, and visit the nearest clinic for a rapid malaria test.",
        },
    },
    ("agri_extension", "pest_and_disease_advisory"): {
        "sw": {
            "reply": "Kwa wadudu wa mahindi, kagua majani mapema asubuhi, ondoa majani yaliyoathirika, na wasiliana na afisa kilimo kuhusu dawa salama.",
        },
        "lg": {
            "reply": "Ku buwuka mu kasooli, kebera ebikoola ku makya nnyo, ggyawo ebirwadde, era weebuuze ku mulambuzi w'ebyobulimi ku ddagala ettuufu.",
        },
        "yo": {
            "reply": "Fun kokoro agbado, ye ewe wo ni kutukutu owuro, yo awon ti o bajẹ kuro, ki o si kan si agbe-oludamoran.",
        },
        "ha": {
            "reply": "Game da kwari a gonar masara, a duba ganyaye da sassafe, a cire wadanda suka lalace, sannan a tuntubi jami'in gona.",
        },
        "fr": {
            "reply": "Contre les ravageurs du mais, inspectez les feuilles tot le matin, retirez les plants touches et consultez votre conseiller agricole.",
        },
        "en": {
            "reply": "For crop pests, inspect maize whorls early morning, remove heavily damaged leaves, and confirm approved biological control locally.",
        },
    },
    ("fintech_momo", "wallet_balance_check"): {
        "sw": {
            "reply": "Kwa usalama wa fedha zako, usitaje PIN kwa sauti. Tumia menyu rasmi ya USSD ya mtandao wako kuangalia salio bila intaneti.",
        },
        "lg": {
            "reply": "Olw'obukuumi bwa ssente zo, toyogera PIN yo mu ddoboozi. Kozesa USSD ya kkampuni yo okukebera ssente awatali yintaneeti.",
        },
        "en": {
            "reply": "For wallet security, never speak your PIN aloud. Dial your mobile money operator official USSD shortcode to inspect live balances offline.",
        },
    },
}


@dataclass
class CascadeConfig:
    """Configuration controlling offline containment, local SLM calls, and cloud spend caps."""

    offline_mode: bool = False
    local_slm_url: str = "http://127.0.0.1:11434/v1/chat/completions"
    local_slm_model: str = "sunflower-gemma4-e2b"
    cloud_url: str | None = None
    cloud_model: str = "gemini-2.5-flash"
    cloud_api_key: str | None = None
    min_confidence_for_offline: float = 0.62
    currency_code: str = "UGX"
    daily_budget_usd: float = 0.25
    spent_today_usd: float = 0.0
    http_timeout_s: float = 4.0


def _call_openai_compatible(
    endpoint: str,
    model: str,
    prompt: str,
    timeout_s: float,
    api_key: str | None = None,
) -> str | None:
    """Perform a single bounded HTTP request to an OpenAI-compatible SLM or cloud gateway."""
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are SautiMesh, a calm voice assistant. Reply in 1-2 short spoken "
                    "sentences matching the user's language without markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 120,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=max(1.0, min(timeout_s, 15.0))) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
        return None
    return None


def _select_reply_language(analysis: CodeSwitchAnalysis) -> str:
    if analysis.primary_language in {"sw", "lg", "yo", "ha", "fr", "en"}:
        return analysis.primary_language
    return "en"


def route_turn(
    analysis: CodeSwitchAnalysis,
    config: CascadeConfig | None = None,
    transport_fn: Any | None = None,
) -> RouteDecision:
    """Execute the offline-first -> local SLM -> budget-gated cloud cascade for one turn."""
    cfg = config or CascadeConfig()
    start = time.perf_counter()
    lang = _select_reply_language(analysis)
    fx_rate = EXCHANGE_RATES_PER_USD.get(cfg.currency_code.upper(), 1.0)
    human_escalation = analysis.urgency == "high" or "bleeding" in analysis.normalized_text
    escalation_reason = (
        f"High-urgency triage detected ({analysis.intent})" if human_escalation else None
    )

    # Stage 1: Deterministic offline playbook containment (zero data, zero cost).
    playbook_key = (analysis.domain, analysis.intent)
    if playbook_key in OFFLINE_PLAYBOOKS and (
        analysis.confidence >= cfg.min_confidence_for_offline or cfg.offline_mode
    ):
        lang_map = OFFLINE_PLAYBOOKS[playbook_key]
        raw_reply = lang_map.get(lang, lang_map.get("en", {})).get(
            "reply",
            "Request recorded safely offline.",
        )
        spoken, sms_text, ussd_text = format_for_voice_and_channels(raw_reply)
        elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
        return RouteDecision(
            tier="offline_rules",
            provider="sautimesh-offline-playbook",
            model="lexicon-v1",
            reply_text=spoken,
            reply_language=lang,
            sms_fallback_text=sms_text,
            ussd_preview_text=ussd_text,
            human_escalation=human_escalation,
            escalation_reason=escalation_reason,
            latency_ms=elapsed_ms,
            estimated_cost_usd=0.0,
            estimated_cost_local=0.0,
            currency_code=cfg.currency_code.upper(),
            cellular_bytes_used=0,
            offline_contained=True,
            confidence=analysis.confidence,
        )

    # Stage 2: Local SLM via Ollama / llama.cpp / Sunflower edge server when online/local.
    call_fn = transport_fn or _call_openai_compatible
    if not cfg.offline_mode and cfg.local_slm_url:
        prompt = (
            f"Primary language: {lang}; Detected: {','.join(analysis.detected_languages)}; "
            f"Intent: {analysis.intent}; Utterance: {analysis.redacted_text}"
        )
        slm_reply = call_fn(
            cfg.local_slm_url,
            cfg.local_slm_model,
            prompt,
            cfg.http_timeout_s,
            None,
        )
        if slm_reply:
            spoken, sms_text, ussd_text = format_for_voice_and_channels(slm_reply)
            elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
            return RouteDecision(
                tier="local_slm",
                provider="edge-slm-openai-compat",
                model=cfg.local_slm_model,
                reply_text=spoken,
                reply_language=lang,
                sms_fallback_text=sms_text,
                ussd_preview_text=ussd_text,
                human_escalation=human_escalation,
                escalation_reason=escalation_reason,
                latency_ms=elapsed_ms,
                estimated_cost_usd=0.0,
                estimated_cost_local=0.0,
                currency_code=cfg.currency_code.upper(),
                cellular_bytes_used=0,
                offline_contained=True,
                confidence=round(max(analysis.confidence, 0.78), 2),
            )

    # Stage 3: Strictly budget-gated and PII-redacted cloud fallback.
    estimated_cloud_usd = 0.0004
    budget_allows = (cfg.spent_today_usd + estimated_cloud_usd) <= cfg.daily_budget_usd
    if not cfg.offline_mode and cfg.cloud_url and budget_allows:
        cloud_reply = call_fn(
            cfg.cloud_url,
            cfg.cloud_model,
            analysis.redacted_text,
            cfg.http_timeout_s,
            cfg.cloud_api_key,
        )
        if cloud_reply:
            spoken, sms_text, ussd_text = format_for_voice_and_channels(cloud_reply)
            elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
            payload_bytes = len(analysis.redacted_text.encode("utf-8")) + len(spoken.encode("utf-8"))
            return RouteDecision(
                tier="cloud_fallback",
                provider="budget-gated-cloud",
                model=cfg.cloud_model,
                reply_text=spoken,
                reply_language=lang,
                sms_fallback_text=sms_text,
                ussd_preview_text=ussd_text,
                human_escalation=human_escalation,
                escalation_reason=escalation_reason,
                latency_ms=elapsed_ms,
                estimated_cost_usd=estimated_cloud_usd,
                estimated_cost_local=round(estimated_cloud_usd * fx_rate, 2),
                currency_code=cfg.currency_code.upper(),
                cellular_bytes_used=payload_bytes,
                offline_contained=False,
                confidence=0.86,
            )

    # Safe offline queued response when no network/SLM is reachable or budget is exhausted.
    fallback_by_lang = {
        "sw": "Mtandao haupatikani au bajeti imefikiwa. Ombi lako limehifadhiwa salama na litajibiwa muunganisho ukirudi.",
        "lg": "Yintaneeti teriiwo oba ssente z'olunaku ziweddeko. Ekibuuzo kyo kiterekeddwa bulungi era kijja kuddamu nga yintaneeti ezzeemu.",
        "yo": "Asopo ko si tabi isuna ti pari. A ti fi ibeere re pamo ni ailewu titi asopo yoo fi pada.",
        "ha": "Babu hanyar sadarwa ko kasafin kudi ya kare. An ajiye sakonka lafiya za a amsa da zarar an samu hanyar sadarwa.",
        "fr": "Connexion indisponible ou budget atteint. Votre demande vocale est enregistree hors ligne et sera synchronisee.",
        "en": "Connectivity is unavailable or the daily budget cap was reached. Your voice note is safely queued offline for sync.",
    }
    raw_reply = fallback_by_lang.get(lang, fallback_by_lang["en"])
    spoken, sms_text, ussd_text = format_for_voice_and_channels(raw_reply)
    elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
    return RouteDecision(
        tier="offline_rules",
        provider="sautimesh-store-and-forward",
        model="offline-queue-v1",
        reply_text=spoken,
        reply_language=lang,
        sms_fallback_text=sms_text,
        ussd_preview_text=ussd_text,
        human_escalation=True,
        escalation_reason="Offline queue fallback or local spend cap enforced",
        latency_ms=elapsed_ms,
        estimated_cost_usd=0.0,
        estimated_cost_local=0.0,
        currency_code=cfg.currency_code.upper(),
        cellular_bytes_used=0,
        offline_contained=True,
        confidence=analysis.confidence,
    )
