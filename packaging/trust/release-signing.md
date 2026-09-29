# Release verification key

`threshold-release-signing.asc` contains the public OpenPGP key for
Threshold source tags and release checksum signatures. Its fingerprint is:

`CFD943DFD8A7D4A5B1B839BD7186251A35457456`

This is the key identified by the v2.0.1 checksum signature and the v2.0.2
source-tag signature. Confirm this fingerprint through a trusted project
channel before importing the key and verifying downloaded signatures.

```sh
gpg --show-keys --fingerprint threshold-release-signing.asc
gpg --import threshold-release-signing.asc
gpg --verify SHA256SUMS.asc SHA256SUMS
```

The AppImage EC bundle uses a separate Ed25519 trust key described in
`README.md`. This public OpenPGP key cannot sign EC bundles or releases.
