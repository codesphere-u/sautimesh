# Getting Started with SautiMesh (`v0.1.0`)

Install and run SautiMesh anywhere Python `3.11+` runs (Linux, macOS, Windows, Raspberry Pi, or Android Termux).

## 1. Install

```bash
git clone https://github.com/codesphere-u/sautimesh.git
cd sautimesh
pip install -e ".[dev]"
```

Optional local Whisper / Piper speech extras:

```bash
pip install -e ".[voice]"
```

## 2. Inspect Audio & Code-Switching

```bash
sautimesh synth-sample sample.wav --text "Habari daktari mtoto ana fever"
sautimesh analyze "Ssebo obuwuka bungi mu kasooli farm yange leero"
sautimesh chat --text "Habari daktari, mtoto ana fever kali leo" --currency KES
```

## 3. Run Benchmarks, Workbench UI & MCP

```bash
sautimesh eval
sautimesh serve --port 8765
sautimesh mcp
```
