# Project Status — Borsa AI Terminal

_Last verified: 2026-08-13._

## Current stage

**Early public release / release hardening.** The core product is implemented and the local security/build gates pass. Clean-machine testing, release signing/branding, live-provider verification, and independent user feedback remain before a stable release claim.

## Verified locally

| Check | Result |
|---|---|
| Engine tests | 64 passed |
| Python lint | Ruff passed |
| Desktop typecheck | Passed |
| Desktop production build | Passed with Vite 7.3.6 |
| npm dependency audit | 0 known vulnerabilities |
| Python dependency audit | 0 known vulnerabilities after upgrading the environment's pip; local package skipped because it is not published on PyPI |
| Python engine bundle | PyInstaller bundle produced |
| Windows unpacked package | Produced with Electron 43.4.0 |
| Package runtime smoke | Bundled engine `/health` passed |
| Windows NSIS installer | Produced; unsigned and using the default Electron icon |
| GitHub Actions | Node 22, deterministic install, npm audit, pip-audit, typecheck, build, Ruff, and pytest configured; remote result must be checked after push |
| Live Finnhub / hosted AI calls | Not verified without intentionally supplied test credentials |

## Implemented areas

- Market-data adapters and local caching
- Symbol universe and search
- Charts, technical indicators, volume profile, and drawing tools
- Watchlists and portfolio tracking
- News, alerts, reports, and scheduling
- Multi-provider AI abstraction
- FastAPI REST/WebSocket engine
- Electron/React desktop application
- Offline/fake-provider automated tests

## Remaining release gates

1. Complete a clean-machine installation and first-run test.
2. Add a project-owned Windows icon and code-sign production installers.
3. Validate live providers with separate test credentials and documented limits.
4. Migrate deprecated `google.generativeai` usage to `google.genai` in a dedicated compatibility change.
5. Obtain independent user/contributor feedback before calling the project stable.

## Known limitations

- BIST universe is currently a curated seed.
- Free market-data sources can be delayed or incomplete.
- AI output is probabilistic and must be checked against source data.
- OpenAPI-to-TypeScript contracts are manually mirrored.
- Python dependency ranges are not fully locked.
- The project has not yet demonstrated broad adoption or ecosystem dependence.
