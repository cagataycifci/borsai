# Code signing policy

This project signs and distributes Windows release artifacts. The signing method differs by channel.

## Windows — SignPath Foundation (pending)

We are applying to the [SignPath Foundation](https://signpath.org/) free code-signing program for open-source projects.

Planned statement (required by the program, if approved):

> Free code signing provided by SignPath.io, certificate by SignPath Foundation

Status: **Pending approval.**

### What will be signed

- Windows installer packages (`.exe`, NSIS) published on GitHub Releases
- The application executable inside those installers

### Build and signing process

- Artifacts are built from this repository using CI (GitHub Actions).
- Only CI-built artifacts from reviewed tags will be submitted for signing.
- The private key is held by SignPath (HSM-backed). This project does not store the private key.
- SHA-256 checksums are published alongside every release.

### Until approval

Local and CI builds remain unsigned test artifacts and are labeled as such. See `docs/SIGNING.md` for the full release signing process and `docs/RELEASE_CHECKLIST.md` for the required verification gates.
