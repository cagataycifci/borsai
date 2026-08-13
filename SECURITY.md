# Security Policy

## Supported versions

Until the first stable release, security fixes are applied to the latest commit on `main` and the latest published pre-release.

## Reporting a vulnerability

Please do not open a public issue for suspected vulnerabilities. Use GitHub Private Vulnerability Reporting when enabled. If it is unavailable, open a minimal issue asking the maintainer for a private contact channel without disclosing technical details.

Include affected version, reproduction steps, impact, and any suggested mitigation. Do not include real API keys, personal portfolio data, or third-party credentials.

## Security boundaries

- API keys must remain in the encrypted local secrets store or environment variables; they must never be bundled into the renderer.
- Electron IPC additions require explicit allow-listing and validation.
- External market/news content is untrusted input and must not be treated as instructions to an AI model.
- Automated trading and order execution are outside the supported scope.

## Financial and AI disclaimer

Market data can be delayed, incomplete, or inaccurate. AI outputs can contain errors or hallucinations. The software is for informational and research use and does not provide financial advice. Verify conclusions against primary sources before making financial decisions.
