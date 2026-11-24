"""Multilingual & code-switching lexicon, PII guard, and GSM-7/UCS-2 packet analyzer."""

from __future__ import annotations

import math
import re
from typing import Any

from sautimesh.models import CodeSwitchAnalysis, LanguageSpan

SUPPORTED_LANGUAGES: dict[str, dict[str, str]] = {
    "sw": {"name": "Swahili (Kiswahili)", "region": "East & Central Africa"},
    "lg": {"name": "Luganda (Oluganda)", "region": "Uganda"},
    "yo": {"name": "Yoruba (Ede Yoruba)", "region": "Nigeria & Benin"},
    "ha": {"name": "Hausa", "region": "West & Sahel Africa"},
    "fr": {"name": "French (Francais)", "region": "West, Central & North Africa / Global"},
    "en": {"name": "English", "region": "Global"},
    "pcm": {"name": "Nigerian Pidgin", "region": "West Africa"},
    "nyn": {"name": "Runyankole-Rukiga", "region": "Western Uganda"},
    "ach": {"name": "Acholi (Leb Acoli)", "region": "Northern Uganda & South Sudan"},
    "rw": {"name": "Kinyarwanda", "region": "Rwanda & Great Lakes"},
}

# Token lexicons intentionally cover everyday greetings, symptoms, crops, and mobile money
# phrases used in mixed urban/rural speech across Africa and global field deployments.
LANGUAGE_LEXICONS: dict[str, dict[str, str]] = {
    "sw": {
        "habari": "hello",
        "jambo": "hello",
        "tafadhali": "please",
        "asante": "thank you",
        "msaada": "help",
        "homa": "fever",
        "mtoto": "child",
        "kichwa": "headache",
        "tumbo": "stomach",
        "dawa": "medicine",
        "kliniki": "clinic",
        "mahindi": "maize",
        "mazao": "crops",
        "wadudu": "pests",
        "mbolea": "fertilizer",
        "mvua": "rain",
        "fedha": "money",
        "salio": "balance",
        "tuma": "send",
        "akaunti": "account",
        "leo": "today",
        "haraka": "urgent",
        "hatari": "danger",
        "damu": "bleeding",
        "nina": "i have",
        "nataka": "i want",
        "angalia": "check",
        "shamba": "farm",
        "bei": "price",
        "soko": "market",
    },
    "lg": {
        "oli": "are you",
        "otya": "how",
        "gyebale": "well done",
        "webale": "thank you",
        "ssebo": "sir",
        "nnyabo": "madam",
        "nnyamba": "help me",
        "obuyambi": "help",
        "omusujja": "fever",
        "omwana": "child",
        "omutwe": "headache",
        "olubuto": "stomach",
        "eddagala": "medicine",
        "eddwaliro": "hospital",
        "kasooli": "maize",
        "ebirime": "crops",
        "obuwuka": "pests",
        "ssente": "money",
        "leero": "today",
        "mangu": "urgent",
        "omusaayi": "bleeding",
        "ndagala": "i want",
        "njagala": "i want",
        "kebera": "check",
        "ennimiro": "farm",
        "bbeeyi": "price",
        "akatale": "market",
        "okufa": "dying",
    },
    "yo": {
        "bawo": "how",
        "ekaaro": "good morning",
        "ese": "thank you",
        "jowo": "please",
        "iranlowo": "help",
        "iba": "fever",
        "omo": "child",
        "ori": "head",
        "inu": "stomach",
        "oogun": "medicine",
        "ileiwosan": "clinic",
        "agbado": "maize",
        "oko": "farm",
        "kokoro": "pests",
        "ojo": "rain",
        "owo": "money",
        "oni": "today",
        "kiakia": "urgent",
        "eje": "bleeding",
        "mo": "i",
        "fe": "want",
        "owo-ori": "tax",
        "oja": "market",
        "ṣe": "do",
        "báwo": "how",
        "ọmọ": "child",
        "owó": "money",
    },
    "ha": {
        "sannu": "hello",
        "ina": "how",
        "kwana": "morning",
        "nagode": "thank you",
        "taimako": "help",
        "zazzabi": "fever",
        "yaro": "child",
        "kai": "head",
        "ciki": "stomach",
        "magani": "medicine",
        "asibiti": "clinic",
        "masara": "maize",
        "gona": "farm",
        "kwari": "pests",
        "ruwa": "water",
        "kudi": "money",
        "yau": "today",
        "gaggawa": "urgent",
        "jini": "bleeding",
        "kasuwa": "market",
        "nawa": "how much",
        "aika": "send",
    },
    "fr": {
        "bonjour": "hello",
        "bonsoir": "good evening",
        "merci": "thank you",
        "aide": "help",
        "urgence": "urgent",
        "fievre": "fever",
        "enfant": "child",
        "clinique": "clinic",
        "hopital": "hospital",
        "medicament": "medicine",
        "mais": "maize",
        "recolte": "crops",
        "prix": "price",
        "marche": "market",
        "argent": "money",
        "solde": "balance",
        "envoyer": "send",
        "aujourdhui": "today",
        "saignement": "bleeding",
        "champ": "farm",
        "verifier": "check",
    },
    "pcm": {
        "howfar": "hello",
        "abeg": "please",
        "wahala": "problem",
        "pikin": "child",
        "bodi": "body",
        "hot": "fever",
        "moni": "money",
        "sharp": "urgent",
        "sharpsharp": "urgent",
        "wetin": "what",
        "dey": "is",
        "make": "let",
    },
    "nyn": {
        "agandi": "hello",
        "webare": "thank you",
        "obuyambi": "help",
        "omutwe": "headache",
        "ebicoori": "maize",
        "empiiha": "money",
        "ahonaaho": "urgent",
    },
    "ach": {
        "kop": "hello",
        "apwoyo": "thank you",
        "kony": "help",
        "lyeto": "fever",
        "latin": "child",
        "yat": "medicine",
        "ot-yat": "clinic",
        "anyogi": "maize",
        "poto": "farm",
        "kot": "rain",
        "cente": "money",
        "cwal": "send",
        "oyot": "urgent",
        "remo": "bleeding",
    },
    "rw": {
        "muraho": "hello",
        "murakoze": "thank you",
        "ubufasha": "help",
        "umuriro": "fever",
        "umwana": "child",
        "umuti": "medicine",
        "ivuriro": "clinic",
        "ibigori": "maize",
        "umurima": "farm",
        "imvura": "rain",
        "amafaranga": "money",
        "ohereza": "send",
        "byihutirwa": "urgent",
        "amaraso": "bleeding",
    },
}

STOPWORDS_BY_LANG: dict[str, set[str]] = {
    "sw": {"na", "ya", "wa", "kwa", "ni", "au", "sana", "yangu", "wangu"},
    "lg": {"mu", "ku", "ne", "ewa", "kyange", "wange", "era"},
    "yo": {"ni", "ti", "si", "ati", "fun", "mi"},
    "ha": {"da", "na", "ta", "ga", "cikin", "don"},
    "fr": {"le", "la", "les", "et", "de", "du", "un", "une", "pour", "mon", "ma", "avec"},
    "ach": {"ki", "ma", "pi", "ka", "dok", "me"},
    "rw": {"no", "mu", "ku", "kuri", "cyane", "bya"},
    "en": {
        "the", "is", "are", "my", "for", "and", "to", "with", "how", "what", "check",
        "balance", "mobile", "money", "fever", "child", "clinic", "crops", "farm",
        "pests", "price", "market", "urgent", "help", "today", "send", "medicine",
        "maize", "rain", "bleeding", "account", "payment", "soil", "fertilizer",
    },
}

DOMAIN_KEYWORDS: dict[str, set[str]] = {
    "health_triage": {
        "fever", "child", "headache", "stomach", "medicine", "clinic", "hospital",
        "bleeding", "dying", "problem", "body", "cough", "breathing", "malaria",
    },
    "agri_extension": {
        "maize", "crops", "pests", "fertilizer", "rain", "farm", "soil", "harvest",
        "army", "armyworm", "blight", "seed",
    },
    "fintech_momo": {
        "money", "balance", "send", "account", "price", "market", "tax", "payment",
        "loan", "float", "agent", "receipt",
    },
}

URGENCY_HIGH_KEYWORDS = {"urgent", "bleeding", "danger", "dying", "critical", "unconscious"}
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d{1,3}[\s-]?)?(?:07\d{8}|\d{9,13})(?!\w)")
PIN_RE = re.compile(r"(?i)\b(pin|otp|passcode)\s*[:=#]?\s*\d{4,6}\b")
NATIONAL_ID_RE = re.compile(r"\b(?:CM|CF|NIN)[A-Z0-9]{8,14}\b")
CURRENCY_RE = re.compile(r"(?i)\b(UGX|KES|NGN|GHS|XOF|ZAR|RWF|TZS|USD)\s*([0-9][0-9,]*(?:\.[0-9]+)?)\b")

GSM7_CHARS = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ "
    "!\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§"
    "¿abcdefghijklmnopqrstuvwxyzäöñüà"
    "^{}\\[~]|€"
)


def detect_sms_encoding(text: str) -> tuple[str, int, int]:
    """Return ('GSM-7' or 'UCS-2', sms_segments, ussd_pages) for carrier-safe paging."""
    if not text:
        return "GSM-7", 1, 1
    is_gsm7 = all(ch in GSM7_CHARS for ch in text)
    if is_gsm7:
        sms_limit, ussd_limit = 160, 182
        encoding = "GSM-7"
    else:
        sms_limit, ussd_limit = 70, 80
        encoding = "UCS-2"
    length = len(text)
    return (
        encoding,
        max(1, math.ceil(length / sms_limit)),
        max(1, math.ceil(length / ussd_limit)),
    )


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Strip phone numbers, mobile-money PINs/OTPs, and national IDs before cloud calls."""
    findings: list[str] = []
    cleaned = text
    if PIN_RE.search(cleaned):
        findings.append("pin_or_otp")
        cleaned = PIN_RE.sub(r"\1=[REDACTED]", cleaned)
    if NATIONAL_ID_RE.search(cleaned):
        findings.append("national_id")
        cleaned = NATIONAL_ID_RE.sub("[NATIONAL_ID]", cleaned)
    if PHONE_RE.search(cleaned):
        findings.append("phone_number")
        cleaned = PHONE_RE.sub("[PHONE]", cleaned)
    return cleaned, findings


def extract_currency_mentions(text: str) -> list[dict[str, Any]]:
    """Extract currency code and numeric amount pairs from an utterance."""
    mentions: list[dict[str, Any]] = []
    for match in CURRENCY_RE.finditer(text):
        code = match.group(1).upper()
        raw_num = match.group(2).replace(",", "")
        try:
            amount = float(raw_num)
        except ValueError:
            continue
        mentions.append({"currency": code, "amount": amount})
    return mentions


def _classify_token(raw_token: str, hint_lang: str | None) -> tuple[str, str]:
    clean = re.sub(r"^[^\w]+|[^\w]+$", "", raw_token.lower())
    if not clean or clean.isdigit():
        return hint_lang or "en", clean or raw_token

    if hint_lang and clean in LANGUAGE_LEXICONS.get(hint_lang, {}):
        return hint_lang, LANGUAGE_LEXICONS[hint_lang][clean]

    for lang_code, lex in LANGUAGE_LEXICONS.items():
        if clean in lex:
            return lang_code, lex[clean]

    for lang_code, stops in STOPWORDS_BY_LANG.items():
        if clean in stops:
            return lang_code, clean

    # Detect Yoruba/French tonal diacritics when exact lexicon word isn't present.
    if any(ch in raw_token.lower() for ch in "ẹọṣàáèéìíòóùú"):
        if any(ch in raw_token.lower() for ch in "ẹọṣ"):
            return "yo", clean
        return "fr", clean

    return hint_lang or "en", clean


def analyze_utterance(text: str, hint_language: str | None = None) -> CodeSwitchAnalysis:
    """Analyze spoken/typed text for language spans, Code-Switch Index, domain, and packet size."""
    tokens = [t for t in text.strip().split() if t]
    spans: list[LanguageSpan] = []
    lang_counts: dict[str, int] = {}

    for tok in tokens:
        lang_code, norm = _classify_token(tok, hint_language)
        spans.append(LanguageSpan(token=tok, lang=lang_code, normalized=norm))
        lang_counts[lang_code] = lang_counts.get(lang_code, 0) + 1

    detected_languages = sorted(lang_counts, key=lambda k: (-lang_counts[k], k))
    primary_language = detected_languages[0] if detected_languages else (hint_language or "en")

    if len(spans) <= 1 or len(lang_counts) <= 1:
        csi = 0.0
    else:
        switches = sum(1 for a, b in zip(spans, spans[1:]) if a.lang != b.lang)
        csi = round(switches / max(1, len(spans) - 1), 3)

    normalized_tokens = [s.normalized for s in spans]
    normalized_text = " ".join(normalized_tokens)
    norm_set = set(normalized_tokens)

    domain_scores = {
        dom: len(norm_set.intersection(keywords))
        for dom, keywords in DOMAIN_KEYWORDS.items()
    }
    best_domain = max(domain_scores, key=lambda k: domain_scores[k])
    top_hits = domain_scores[best_domain]
    if top_hits == 0:
        domain = "general_civic"
        confidence = 0.48
    else:
        domain = best_domain
        confidence = round(min(0.96, 0.62 + 0.12 * top_hits), 2)

    urgency = "high" if norm_set.intersection(URGENCY_HIGH_KEYWORDS) else "normal"
    intent = _infer_intent(domain, norm_set, urgency)
    redacted_text, pii_found = redact_pii(text)
    currency_mentions = extract_currency_mentions(text)
    sms_encoding, sms_segments, ussd_pages = detect_sms_encoding(text)

    return CodeSwitchAnalysis(
        original_text=text,
        normalized_text=normalized_text,
        redacted_text=redacted_text,
        primary_language=primary_language,
        detected_languages=detected_languages or [primary_language],
        code_switch_index=csi,
        spans=spans,
        domain=domain,
        intent=intent,
        confidence=confidence,
        urgency=urgency,
        currency_mentions=currency_mentions,
        sms_encoding=sms_encoding,
        sms_segments=sms_segments,
        ussd_pages=ussd_pages,
        pii_redacted=pii_found,
    )


def _infer_intent(domain: str, norm_set: set[str], urgency: str) -> str:
    if domain == "health_triage":
        if urgency == "high":
            return "emergency_referral"
        if "fever" in norm_set and "child" in norm_set:
            return "pediatric_fever_triage"
        return "symptom_intake"
    if domain == "agri_extension":
        if "pests" in norm_set or "armyworm" in norm_set or "blight" in norm_set:
            return "pest_and_disease_advisory"
        if "price" in norm_set or "market" in norm_set:
            return "market_price_lookup"
        return "crop_calendar_advice"
    if domain == "fintech_momo":
        if "balance" in norm_set or "check" in norm_set:
            return "wallet_balance_check"
        if "send" in norm_set or "payment" in norm_set:
            return "transfer_precheck"
        return "merchant_pricing_help"
    return "general_information"
