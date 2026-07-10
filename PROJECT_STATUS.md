# PROJECT_STATUS.md — Borsa AI Terminal

_Last updated: 2026-07-09 (Phase 10 Hardening complete)._

## Overall completion
**100%** (10 of 10 phases complete).

| Metric | Value |
|---|---|
| Phases complete | 10 / 10 |
| Current phase | **All phases complete** |
| Engine tests | 59 passing · ruff clean (app) |
| Desktop | typecheck + build pass; CI configured |
| Symbol universe | 12,610 symbols (US live + BIST seed) |

## Current phase
All 10 phases are **complete**. The terminal ships with market data, charts,
watchlists, portfolio, news, AI, alerts, scheduled reports, global search,
commentator consensus, CI, and packaging scaffolding (PyInstaller + electron-builder).

## Remaining / follow-up
- **Live verification** of PyInstaller bundle + electron-builder installer on Windows
  (run `npm run package` after `npm install`).
- **BIST full listing** via KAP scraper (seed ~113 names today).
- **Finnhub / AI live keys** unverified on dev machine (covered by fakes in tests).
- **OpenAPI→TS codegen** — contracts are hand-mirrored; automate in a future pass.

## Technical debt
1. BIST universe is a curated seed, not the full listing.
2. Finnhub + AI providers unverified without API keys.
3. TS contracts hand-mirrored from Pydantic.
4. WS streaming polls every 5s (free tier).
5. Economic calendar uses offline recurring logic (no live macro feed).

## Health / blockers
- Blockers: **none**.
- Build/run: ✅ 59 engine tests + ruff + desktop typecheck + build + GitHub Actions CI.
