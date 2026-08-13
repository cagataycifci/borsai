# Project Status — Borsa AI Terminal

_Last verified: 2026-08-12._

## Current stage

**Early public release / OSS hardening.** Core product modules are implemented, but release engineering, dependency remediation, live-provider verification, and independent user testing remain in progress.

## Verified locally

| Check | Result |
|---|---|
| Engine tests | 64 passed; 1 third-party deprecation warning |
| Python lint | Ruff passed |
| Desktop typecheck | Passed |
| Desktop production build | Passed |
| GitHub Actions | Workflow present; remote result must be checked after push |
| npm dependency audit | 24 findings: 2 moderate, 21 high, 1 critical |
| Windows installer | Not verified in this audit |
| Live Finnhub / hosted AI calls | Not verified without user credentials |

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

## Release blockers

1. Triage and remediate npm audit findings without untested forced upgrades.
2. Verify a normal clean `npm ci`, including Electron binary installation.
3. Build and smoke-test the Windows installer and bundled Python engine.
4. Complete at least one independent clean-machine installation test.
5. Validate live provider behavior with intentionally supplied test credentials.

## Known limitations

- BIST universe is currently a curated seed.
- Free market-data sources can be delayed or incomplete.
- AI output is probabilistic and must be checked against source data.
- OpenAPI-to-TypeScript contracts are manually mirrored.
- The project has not yet demonstrated broad adoption or ecosystem dependence.
