# Borsa AI Terminal

An AI-powered desktop market terminal for **Borsa Istanbul (BIST)** and **US
markets (NYSE / NASDAQ / AMEX)** — like a personal, AI-driven Bloomberg Terminal.

- **UI:** Electron + React + TypeScript (dark, dockable, TradingView-style)
- **Engine:** Python FastAPI sidecar (quant, data, news, AI, scheduler)
- **Data:** free-tier (yfinance + Finnhub) behind swappable adapters
- **AI:** multi-provider (Claude / OpenAI / Gemini / Ollama), chosen in Settings

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design and
[`docs/ROADMAP.md`](docs/ROADMAP.md) for phase status.

## Prerequisites
- Node.js >= 20 and npm
- Python >= 3.11

## Setup

```bash
# 1. Install JS deps (root + workspaces)
npm install

# 2. Set up the Python engine
cd services/engine
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
cd ../..
```

## Run (development)

```bash
# Boots the Python engine AND the Electron desktop app together
npm run dev
```

Or individually:

```bash
npm run dev:engine    # FastAPI on 127.0.0.1:8787
npm run dev:desktop   # Electron + Vite
```

When running via the packaged app, the engine is spawned and supervised
automatically by the Electron main process.

## Package (production build)

```bash
# Build the PyInstaller engine bundle, then the Electron installer
npm run package
```

Engine output: `services/engine/dist/borsa-engine/`  
Desktop installer: `apps/desktop/release/`

## CI

GitHub Actions runs engine tests + ruff and desktop typecheck/build on push/PR
(see `.github/workflows/ci.yml`).

## Project structure

```
apps/desktop      Electron + React app
services/engine   Python FastAPI engine
docs              Architecture, roadmap, handoff
scripts           Dev orchestration scripts
```

> **Disclaimer:** This software provides evidence-based analysis for
> informational purposes only. It does not provide financial advice.
