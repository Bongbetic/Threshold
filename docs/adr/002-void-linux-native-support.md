# Support Void Linux through native XBPS and runit integration

Threshold supports current `x86_64-glibc` Void Linux through one unified XBPS package containing the application, MSI EC source, and native integration payload. The project maintains and tests the template before proposing it to `void-packages`; it does not publish standalone `.xbps` release candidates or operate a third-party repository because that would create a separate signing and repository trust boundary.

Void uses XBPS DKMS hooks and an installed-but-disabled runit service. The administrator explicitly enables boot reconciliation; it runs once and then pauses so runit cannot turn a bounded reconciliation into an unbounded retry loop. A dedicated `threshold` group limits sysfs write authority, Secure Boot signing remains administrator-owned, and support requires both continuous `x86_64-glibc` CI and a recorded physical-machine acceptance run.
