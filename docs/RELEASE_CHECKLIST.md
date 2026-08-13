# Release checklist

## Required gates

- [ ] Release commit reviewed and CI green
- [ ] `npm audit` and `pip-audit` report no known vulnerabilities
- [ ] Ruff, pytest, desktop typecheck, and production build pass
- [ ] PyInstaller engine bundle produced
- [ ] Unpacked desktop package passes bundled-engine health smoke test
- [ ] NSIS installer installs into a fresh directory and starts successfully
- [ ] Project icon and executable metadata verified
- [ ] Installer and executable Authenticode signatures verified
- [ ] SHA-256 checksums generated and published
- [ ] Live-provider tests run with dedicated test credentials
- [ ] Release notes state limitations and financial-software disclaimer

Unsigned local installers must be labeled as test artifacts and must not be described as production-ready.
