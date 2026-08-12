# Dependency and Licensing Notes

_Last reviewed: 2026-08-12._

## Project license

Borsa AI Terminal is distributed under the MIT License. Third-party packages and external data remain subject to their own licenses and terms.

## Major software dependencies

- FastAPI, Pydantic, SQLAlchemy and related Python packages
- yfinance and optional Finnhub market-data adapters
- Anthropic, OpenAI-compatible, Gemini and Ollama AI adapters
- Electron, React, Vite, dockview and lightweight-charts

Exact versions are recorded in `package-lock.json` for Node dependencies. Python dependencies are declared in `services/engine/pyproject.toml` with minimum versions; fully locked Python builds remain a follow-up item.

## External data and services

- yfinance/Yahoo data is best-effort and may be delayed. Users are responsible for complying with provider terms.
- Finnhub requires the user's own key and is subject to Finnhub terms and rate limits.
- BIST/KAP information must not be redistributed in ways that violate source or vendor terms.
- AI providers require users' own credentials unless a local provider such as Ollama is used.

## Distribution checklist

Before publishing a release:

1. Run the test, lint, typecheck and build commands from the README.
2. Run `npm audit` and a Python dependency audit tool.
3. Review bundled Electron and PyInstaller contents.
4. Confirm that no API keys, databases, logs, build caches, or licensed market data are included.
5. Record unresolved findings in the release notes.

This document is an engineering inventory, not legal advice.
