# Changelog

All notable changes to **SautiMesh** are documented in this file.

## [0.1.0] - 2026-11-15
### Added
- **Zero-Bloat Python 3.11+ Core Runtime**: Runs cleanly on standard library dependencies across Linux, macOS, Raspberry Pi, and Android Termux, with optional adapters for `faster-whisper`, `whisper.cpp`, `sherpa-onnx`, `Piper`, `Sunbird Sunflower v2`, `USOAL Luganda TTS`, `Ollama`, and OpenAI-compatible endpoints.
- **Code-Switching & Multilingual Lexicon Engine (`sautimesh.languages`)**: Token-level span tagging, Code-Switch Index (CSI), currency normalization (`UGX`, `KES`, `NGN`, `GHS`, `XOF`, `ZAR`, `RWF`, `USD`), PII redaction, and GSM-7 vs. UCS-2 byte-aware SMS/USSD packing across **Swahili (`sw`)**, **Luganda (`lg`)**, **Yoruba (`yo`)**, **Hausa (`ha`)**, **French (`fr`)**, **English (`en`)**, **Nigerian Pidgin (`pcm`)**, and **Runyankole (`nyn`)**.
- **Edge-to-Cloud Model Cascade (`sautimesh.cascade`)**: Deterministic offline rule & domain workflow containment first (`0 ms` external latency, `0` cellular bytes), escalating only when confidence falls below threshold and local-currency budget permits.
- **Digital Audio & VAD Pipeline (`sautimesh.audio`)**: Pure-Python `16 kHz` 16-bit PCM WAV synthesis/inspection, RMS + zero-crossing Voice Activity Detection (VAD), SNR estimation, and mobile-data footprint estimator (`12 kbps` AMR / `16 kbps` Opus).
- **Crash-Proof SQLite Store-and-Forward Queue (`sautimesh.store`)**: WAL-backed ACID persistence for sessions, turn audit logs, idempotent webhook replay, and retry/dead-letter synchronization across intermittent cellular connectivity.
- **DPGA Open AI Transparency & Evaluation (`sautimesh.dpg`, `sautimesh.eval`)**: Built-in multilingual code-switching benchmark runner and Digital Public Goods Model & Limitation Card generator.
- **CLI, Local Interactive Voice Workbench & Stdio MCP Server**: `sautimesh analyze`, `chat`, `eval`, `sync`, `dpg-card`, `doctor`, `serve`, and `mcp`.
