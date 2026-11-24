"""Deterministic WER, CER, and Code-Switch Span Accuracy evaluation harness for edge ASR."""

from __future__ import annotations

import re
from dataclasses import dataclass

from sautimesh.languages import analyze_utterance

_PUNCT_RE = re.compile(r"[^\w\s]", flags=re.UNICODE)


def _normalize_text(text: str) -> str:
    return " ".join(_PUNCT_RE.sub(" ", text.lower()).split())


def _levenshtein(seq_a: list[str], seq_b: list[str]) -> int:
    if seq_a == seq_b:
        return 0
    if not seq_a:
        return len(seq_b)
    if not seq_b:
        return len(seq_a)
    prev = list(range(len(seq_b) + 1))
    for i, item_a in enumerate(seq_a, start=1):
        curr = [i]
        for j, item_b in enumerate(seq_b, start=1):
            cost = 0 if item_a == item_b else 1
            curr.append(min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


@dataclass(frozen=True)
class UtteranceEvalResult:
    reference: str
    hypothesis: str
    wer: float
    cer: float
    ref_languages: tuple[str, ...]
    hyp_languages: tuple[str, ...]
    language_recall: float
    domain_match: bool


@dataclass(frozen=True)
class BenchmarkEvalSummary:
    sample_count: int
    mean_wer: float
    mean_cer: float
    mean_language_recall: float
    domain_accuracy: float
    samples: tuple[UtteranceEvalResult, ...]


def word_error_rate(reference: str, hypothesis: str) -> float:
    """Compute Word Error Rate (WER) via edit distance over normalized tokens."""
    ref_words = _normalize_text(reference).split()
    hyp_words = _normalize_text(hypothesis).split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    return round(_levenshtein(ref_words, hyp_words) / len(ref_words), 4)


def char_error_rate(reference: str, hypothesis: str) -> float:
    """Compute Character Error Rate (CER) over normalized non-whitespace characters."""
    ref_chars = list(_normalize_text(reference).replace(" ", ""))
    hyp_chars = list(_normalize_text(hypothesis).replace(" ", ""))
    if not ref_chars:
        return 0.0 if not hyp_chars else 1.0
    return round(_levenshtein(ref_chars, hyp_chars) / len(ref_chars), 4)


def evaluate_asr_sample(reference: str, hypothesis: str) -> UtteranceEvalResult:
    """Evaluate one ASR hypothesis against ground-truth code-switched reference text."""
    ref_analysis = analyze_utterance(reference)
    hyp_analysis = analyze_utterance(hypothesis)
    ref_langs = set(ref_analysis.detected_languages)
    hyp_langs = set(hyp_analysis.detected_languages)
    lang_recall = (len(ref_langs & hyp_langs) / len(ref_langs)) if ref_langs else 1.0
    return UtteranceEvalResult(
        reference=reference,
        hypothesis=hypothesis,
        wer=word_error_rate(reference, hypothesis),
        cer=char_error_rate(reference, hypothesis),
        ref_languages=tuple(sorted(ref_langs)),
        hyp_languages=tuple(sorted(hyp_langs)),
        language_recall=round(lang_recall, 4),
        domain_match=(ref_analysis.domain == hyp_analysis.domain),
    )


def evaluate_asr_benchmark(pairs: list[tuple[str, str]]) -> BenchmarkEvalSummary:
    """Aggregate WER, CER, code-switch language recall, and domain preservation across a corpus."""
    if not pairs:
        raise ValueError("Evaluation corpus cannot be empty")
    results = tuple(evaluate_asr_sample(ref, hyp) for ref, hyp in pairs)
    n = len(results)
    return BenchmarkEvalSummary(
        sample_count=n,
        mean_wer=round(sum(r.wer for r in results) / n, 4),
        mean_cer=round(sum(r.cer for r in results) / n, 4),
        mean_language_recall=round(sum(r.language_recall for r in results) / n, 4),
        domain_accuracy=round(sum(1 for r in results if r.domain_match) / n, 4),
        samples=results,
    )
