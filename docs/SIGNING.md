# Windows signing

Production installers must be Authenticode-signed with a certificate controlled by the project owner. Private keys must never be committed or uploaded as ordinary repository files.

## Release process

1. Obtain an organization-validated or extended-validation code-signing certificate from a trusted certificate authority.
2. Store the signing credential in a hardware-backed service or GitHub Actions secret/provider integration.
3. Build from a reviewed tag on a clean runner.
4. Sign the application executable and NSIS installer.
5. Verify with `Get-AuthenticodeSignature` and Windows SmartScreen testing.
6. Publish SHA-256 checksums with every release.

Local and pull-request builds intentionally use `signExecutable: false`. They are suitable for testing, not for a production trust claim.
