# Code Audit and Verification

_Last verified: 2026-08-13 on Windows, Python 3.12 and Node 24._

## Repository recovery

The canonical GitHub snapshot was recovered into a separate working directory and matched commit `2134092`. The earlier minimal scaffold remains preserved separately and was not pushed over the canonical project.

## Verified successfully

- Python environment and editable engine installation completed.
- `python -m ruff check app`: passed.
- Engine test suite: **64 passed**.
- Desktop TypeScript typecheck: passed.
- Electron/Vite production build: passed with Electron 43.4.0, electron-builder 26.15.3, electron-vite 5.0.0, and Vite 7.3.6.
- `npm audit`: **0 known vulnerabilities** after tested dependency upgrades.
- `pip-audit`: **0 known vulnerabilities** after upgrading the audit environments' `pip`; the local unpublished `borsa-engine` package was skipped as expected.
- PyInstaller engine bundle produced successfully.
- Windows unpacked Electron package produced successfully.
- Package smoke test started the bundled engine and received a healthy `/health` response.
- NSIS installer produced successfully.
- The repository contains real FastAPI routes, WebSocket support, data/AI adapters, persistence, migrations, Electron main/preload/renderer code, and offline tests.

## Open findings

1. A normal Electron postinstall/download was unreliable on the current network. The official Electron 43.4.0 archive was downloaded separately, verified against the release `SHASUMS256.txt`, and used for packaging. A clean-machine install remains required.
2. The generated Windows installer is unsigned and currently uses the default Electron icon.
3. PyInstaller reports that `google.generativeai` is deprecated; migrate to `google.genai` in a separately tested compatibility change.
4. Live Finnhub and hosted AI-provider calls were not tested because no credentials were used.
5. BIST universe coverage remains a curated seed rather than a guaranteed complete official list.
6. Python dependencies use minimum-version ranges and are not fully locked.
7. Public user testing and external contributor evidence are still absent.

## Release gate

Do not describe the project as stable or production-ready until a clean-machine installation succeeds, production installers are branded and signed, live-provider behavior is validated with test credentials, and at least one independent user completes the documented setup.
