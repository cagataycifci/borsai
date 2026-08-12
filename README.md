# Borsa AI Terminal

[![CI](https://github.com/cagataycifci/borsai/actions/workflows/ci.yml/badge.svg)](https://github.com/cagataycifci/borsai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An open-source desktop market terminal for **Borsa Istanbul (BIST)** and **US markets**. It combines an Electron/React interface with a local FastAPI engine for market data, charts, watchlists, portfolio tracking, news, alerts, reports, and optional AI-assisted analysis.

> Project status: early public release. Core modules and automated tests exist, but installer verification, live-provider coverage, and independent user testing are still in progress.

## Highlights

- Electron + React + TypeScript desktop interface
- FastAPI engine with REST and WebSocket APIs
- BIST and US symbol search with yfinance/Finnhub adapters
- Charts, indicators, volume profile, and drawing tools
- Watchlists, portfolio tracking, alerts, news, and scheduled reports
- Optional Claude, OpenAI, Gemini, and Ollama adapters
- Local encrypted secrets store; keys are not exposed to the renderer
- Offline/fake-provider test coverage for core behavior

## Important limitations

- Market data can be delayed, incomplete, or inaccurate.
- BIST coverage currently uses a curated seed rather than a guaranteed complete official listing.
- Live Finnhub and hosted AI-provider calls require users' own API keys and are not covered by offline CI.
- Packaging scaffolding exists, but the Windows installer must be verified before a stable release.
- This software is informational and does not provide financial advice or automated trade execution.

## Prerequisites

- Node.js 20 or newer
- Python 3.11 or newer
- npm

## Quick start

### Windows helper

```powershell
.\setup.ps1
```

### Manual setup

```bash
npm install
cd services/engine
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cd ../..
```

Run both components:

```bash
npm run dev
```

Or run them separately:

```bash
npm run dev:engine
npm run dev:desktop
```

## Validation

```bash
cd services/engine
python -m ruff check app
python -m pytest -q
cd ../..
npm run typecheck -w apps/desktop
npm run build -w apps/desktop
```

## Production packaging

```bash
npm run package
```

The engine bundle is written under `services/engine/dist/`; desktop artifacts are written under `apps/desktop/release/`.

## Project structure

```text
apps/desktop      Electron + React desktop application
services/engine   FastAPI engine, data/AI adapters, persistence and tests
docs              Architecture, roadmap, audit and licensing notes
scripts           Development and packaging orchestration
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)
- [Current status](PROJECT_STATUS.md)
- [Security policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Dependency and licensing notes](docs/DEPENDENCY_AND_LICENSES.md)

## License

MIT. See [LICENSE](LICENSE).
