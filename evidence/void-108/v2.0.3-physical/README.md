# v2.0.3 physical upgrade rejection

Candidate: `threshold-2.0.3_1.x86_64.xbps`  
SHA-256: `2985d08b832997074138491c458e21258edd958af01552bac8e5750877a467e4`  
Source: `66956756eb0d33f2c3ccc4c67492cbe27c197bf5`  
Observed: 2026-09-29, MSI Thin A15 B7UCX, Void glibc, kernel `7.2.8_1`.

The exact draft passed inventory verification and clean-container package
verification. Real upgrade from the installed v2.0.2 in the same boot failed
EC lifecycle acceptance: the old REMOVE hook deleted managed DKMS registration,
then an earlier `install-or-upgrade` journal entry caused setup to be skipped.
The package transaction itself reported success. The live module remained
loaded and the active threshold stayed at 60%, but no managed DKMS registration
remained on disk. No reboot was attempted in that state.

An explicit administrative `repair` restored the managed module on disk;
`dkms status -m msi-ec` again reported `7.2.8_1` installed, and `modinfo -n`
resolved the newly installed module. Repair also exposed missing `zstd` on the
host: DKMS fell back to an uncompressed `.ko`. The corrected Void recipe adds
this runtime compression dependency. Active threshold remains 60%.

The candidate remains an unpublished rejected draft. Successful manual repair
is recovery evidence, not a passing upgrade gate. v2.0.4 uses fresh journal
attempts for package transactions and explicit repairs; only boot reconciliation
is deduplicated by boot identity. The Void REMOVE hook also preserves managed
builds and kernel records during upgrades, using the documented UPDATE flag:
[official void-packages manual](https://github.com/void-linux/void-packages/blob/master/Manual.md#install-and-remove-files).

Regression tests reproduce same-boot removal/reinstallation and failed-repair
retry, and distinguish upgrade/removal hook execution. They are automated proof,
not physical acceptance of the next candidate. No full acceptance report exists.
