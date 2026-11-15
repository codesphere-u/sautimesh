# SautiMesh

> **Voice-first, offline-first multilingual and code-switching AI agent runtime for Africa and the global edge.**

[![Version](https://img.shields.io/badge/version-v0.1.0-f59e0b)](https://github.com/codesphere-u/sautimesh/releases)
[![Python](https://img.shields.io/badge/python-3.11%2B-0284c7)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-15803d)](./LICENSE)
[![DPG Aligned](https://img.shields.io/badge/DPG-Open_AI_Transparency-0284c7)](./docs/ARCHITECTURE_AND_DPG.md)

**SautiMesh** (*Sauti* = Voice in Swahili + *Mesh* = resilient edge-first durability) empowers community health workers, smallholder cooperatives, emergency responders, mobile money agents, and global field developers to build **offline-first voice agents** across **Swahili (`sw`), Luganda (`lg`), Yoruba (`yo`), Hausa (`ha`), French (`fr`), English (`en`), Nigerian Pidgin (`pcm`), and Runyankole (`nyn`)** without burning mobile data or USD cloud budgets.

---

## Why SautiMesh Exists (Research-Backed Design)

Mainstream agent frameworks (`LangGraph`, `CrewAI`, `AutoGen`) assume continuous broadband, English-only inputs, and cloud Postgres/API connectivity. Real-world field deployments show why that fails:

1. **Connectivity & Power Reality (GSMA & IEA):** Roughly 63% of Africa lives within broadband coverage yet stays offline, and nearly 600M lack reliable power. Agents need ACID local persistence (**SQLite WAL**) and store-and-forward retry queues instead of split-brain cloud sessions.
2. **Code-Switching Speech Reality (Masakhane, Sunbird AI, Lelapa AI):** Real speakers naturally mix languages mid-sentence (*"Habari daktari, mtoto ana fever kali leo"*). SautiMesh tags tokens per language, computes a **Code-Switch Index (CSI)**, preserves tonal diacritics (`ẹ, ọ, ṣ`), and grounds idioms before reaching an LLM.
3. **Budget & Carrier Physics:** USSD caps packets at **160 bytes** (**182 GSM-7** / **80 UCS-2** chars) and SMS splits at **160 GSM-7 / 70 UCS-2**. SautiMesh formats every spoken agent reply with single-SMS fallback, USSD pagination summaries, **local-currency (`UGX, KES, NGN, GHS, XOF, ZAR, RWF, TZS, USD`)** hard spend caps, and local **PII redaction** before cloud calls.

---

## Core Architecture

```text
 16kHz PCM / Voice Note ──▶ Pure-Python VAD & SNR Check (or Silero / whisper.cpp / MMS)
                                     │
                                     ▼
                     Code-Switch & Lexicon Guard
        (sw / lg / yo / ha / fr / en / pcm / nyn · PII Redact · GSM-7/UCS-2 Pack)
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
   Stage 1: Offline Playbooks   Stage 2: Edge SLM          Stage 3: Gated Cloud
   (0 ms · 0 bytes · $0.00)     (Ollama / Sunflower v2)   (FX Cap + PII Stripped)
         └───────────────────────────┼───────────────────────────┘
                                     ▼
             SQLite WAL Store-and-Forward Queue + Spoken WAV & SMS Receipt
```

---

## Quickstart

Zero external runtime dependencies required on Python `3.11+`:

```bash
git clone https://github.com/codesphere-u/sautimesh.git
cd sautimesh
pip install -e .

# Analyze a mixed Swahili + English utterance with PII redaction
sautimesh analyze "Habari daktari, mtoto ana fever kali leo PIN: 4829"

# Execute a deterministic offline-first voice turn with SQLite persistence
sautimesh chat --text "Ssebo obuwuka bungi mu kasooli farm yange leero" --currency UGX

# Run the built-in 7-case multilingual & emergency-escalation benchmark suite
sautimesh eval

# Start the interactive Voice Workbench & Simulator at http://127.0.0.1:8765
sautimesh serve

# Export DPGA Open Source AI Transparency & Limitation Card
sautimesh dpg-card --format markdown
```

---

## Pluggable Speech & Model Adapters

SautiMesh ships zero-bloat pure-Python fallbacks (`OfflineAcousticFallbackASR`, `OfflineCadenceTTS`) so tests, CI gates, and Termux Android phones run reliably anywhere, while supporting drop-in CLI/HTTP adapters for:
- **Sunbird AI Sunflower v2 / Gemma Edge** (67 African languages) & **USOAL Luganda TTS**
- **`faster-whisper` / `whisper.cpp` / Meta MMS / Sherpa-ONNX** ASR
- **Piper ONNX TTS** & **Ollama / `llama.cpp` OpenAI-compatible SLM gateways**

---

## Model Context Protocol (MCP) Server

Run SautiMesh as a zero-dependency stdio MCP tool server inside Claude Code, Cursor, Codex, or Antigravity:

```bash
sautimesh mcp
```

Exposes 5 native MCP tools: `sautimesh_analyze_utterance`, `sautimesh_run_voice_turn`, `sautimesh_run_benchmark`, `sautimesh_sync_outbox`, and `sautimesh_export_dpg_card`.

---

## Documentation & Links

- **Live Website:** https://codesphere-u.github.io/sautimesh/
- **Interactive Voice Studio:** https://codesphere-u.github.io/sautimesh/studio.html
- **Research & Proof:** https://codesphere-u.github.io/sautimesh/proof.html
- **Documentation:** https://codesphere-u.github.io/sautimesh/docs.html
- **Guides:** [Getting Started](./docs/GETTING_STARTED.md) · [Architecture & DPG Card](./docs/ARCHITECTURE_AND_DPG.md)
- **AI Discovery:** [`llms.txt`](./llms.txt) · [`llms-full.txt`](./llms-full.txt) · [`CITATION.cff`](./CITATION.cff)
