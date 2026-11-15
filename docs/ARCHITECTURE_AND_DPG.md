# Architecture & Digital Public Goods (DPG) Alignment

SautiMesh follows open-source Digital Public Goods principles for high-resilience voice agents:

1. **Store-and-Forward Durability (`sautimesh/store.py`)**: Uses SQLite WAL mode with idempotent message deduplication (`idempotency_key`), bounded retries (`MAX_RETRIES=3`), and `DEAD_LETTER` isolation.
2. **Code-Switch & Cultural Context Guard (`sautimesh/languages.py`)**: Detects token-level language spans across 8 languages, calculates Code-Switch Index (CSI), strips local PIN/OTP/Phone/ID PII prior to remote transport, and calculates GSM-7 (`182`/`160`) vs UCS-2 (`80`/`70`) character limits.
3. **Edge-First Cascade (`sautimesh/cascade.py`)**: Stage 1 (`offline_rules`) resolves critical health, agricultural, and mobile-money safety queries in `0 ms` with `0` cellular bytes. Stage 2 (`local_slm`) queries local Ollama/Sunflower GGUF gateways with bounded timeouts (`timeout=4.0s`). Stage 3 (`cloud_fallback`) runs only within daily USD/local FX caps.
4. **Human Extension Safety Escalation**: Any high-urgency symptom (e.g., bleeding, unconsciousness, critical fever) immediately flags `human_escalation=True` and queues a structured alert onto the local outbox.
