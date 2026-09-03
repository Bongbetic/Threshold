# Threshold EC bundle trust key

The AppImage EC bootstrap (`packaging/threshold-appimage-bootstrap`)
verifies every streamed EC bundle manifest against one pinned Ed25519
public key installed at:

    /usr/share/threshold/trust/threshold-ec-trust.pub

## Maintainer operations

Generate the maintainer signing keypair (offline machine):

    openssl genpkey -algorithm ed25519 -out threshold-ec-signing.pem
    openssl pkey -in threshold-ec-signing.pem -pubout -out threshold-ec-trust.pub

- The **private** key (`threshold-ec-signing.pem`) never enters the
  repository. Release CI receives it as a protected secret and passes it
  to `packaging/appimage/build-appimage.sh` via `THRESHOLD_EC_SIGNING_KEY`.
- The **public** key is shipped in every artifact at the path above and
  recorded in the release manifest. Rotation is cross-signed: a trusted
  key introduces the successor through signed trust metadata; a broken
  trust chain requires an explicit rebootstrap.

The signing key in CI is scoped to the `release-promotion` protected
environment; ordinary downgrades are refused by sequence, and emergency
rollback ships as a newly signed higher-sequence bundle.
