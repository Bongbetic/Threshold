
# Verification Procedure: Privileged Fake-System Lifecycle Scenarios

## Overview
Test all EC lifecycle scenarios using the real lifecycle script with substituted
effects, covering preflight, setup states, transaction failure injection, rollback,
MOK pending state, reconciliation, migration, collisions, kernel updates, repair,
removal, locking, idempotency, and bounded evidence.

## Prerequisites
- Test environment with substituted DKMS, module, Secure Boot, udev, boot identity, and sysfs effects
- Real lifecycle script: `packaging/threshold-ec-lifecycle`
- Python test framework with pytest

## Test Scenarios

### 1. Non-MSI Hardware Preflight
```bash
# Test that non-MSI hardware never builds or loads msi-ec
# (Covered by test_ec_lifecycle_fake.py::test_non_msi_hardware_never_builds_or_loads)
```

### 2. MSI Hardware Setup States
```bash
# Test available state
# (Covered by test_ec_lifecycle_fake.py::test_setup_available_on_msi_hardware)

# Test pending_reboot state
# (Covered by test_ec_lifecycle_fake.py::test_pending_reboot_state)

# Test unavailable state with reasons
# (Covered by test_ec_lifecycle_fake.py::test_unavailable_with_reasons)
```

### 3. Transaction Failure Injection
```bash
# Test DKMS build failure
# (Covered by test_ec_lifecycle_fake.py::test_dkms_build_failure)

# Test module load failure
# (Covered by test_ec_lifecycle_fake.py::test_module_load_failure)

# Test sysfs write failure
# (Covered by test_ec_lifecycle_fake.py::test_sysfs_write_failure)
```

### 4. Rollback Scenarios
```bash
# Test transaction rollback on failure
# (Covered by test_ec_lifecycle_fake.py::test_transaction_rollback)

# Test last-known-good preservation
# (Covered by test_ec_lifecycle_fake.py::test_last_known_good_preservation)
```

### 5. MOK Pending State
```bash
# Test MOK enrollment required
# (Covered by test_ec_lifecycle_fake.py::test_mok_enrollment_required)

# Test pending reboot consumption
# (Covered by test_ec_lifecycle_fake.py::test_pending_reboot_consumption)
```

### 6. Boot Reconciliation
```bash
# Test bounded reconciliation
# (Covered by test_ec_lifecycle_fake.py::test_bounded_reconciliation)

# Test no-op when active and desired match
# (Covered by test_ec_lifecycle_fake.py::test_noop_when_thresholds_match)

# Test one-write/readback behavior
# (Covered by test_ec_lifecycle_fake.py::test_one_write_readback)
```

### 7. Migration Scenarios
```bash
# Test paired-RPM handoff
# (Covered by test_ec_lifecycle_fake.py::test_migration_handoff)

# Test foreign source collision
# (Covered by test_ec_lifecycle_fake.py::test_foreign_source_collision)

# Test foreign registration collision
# (Covered by test_ec_lifecycle_fake.py::test_foreign_registration_collision)
```

### 8. Kernel Updates
```bash
# Test per-kernel isolation
# (Covered by test_ec_lifecycle_fake.py::test_per_kernel_isolation)

# Test known-good qualification
# (Covered by test_ec_lifecycle_fake.py::test_known_good_qualification)

# Test offline repair
# (Covered by test_ec_lifecycle_fake.py::test_offline_repair)
```

### 9. Repair and Removal
```bash
# Test repair preserves live control
# (Covered by test_ec_lifecycle_fake.py::test_repair_preserves_live_control)

# Test removal semantics
# (Covered by test_ec_lifecycle_fake.py::test_removal_semantics)

# Test foreign asset preservation
# (Covered by test_ec_lifecycle_fake.py::test_foreign_asset_preservation)
```

### 10. Locking and Idempotency
```bash
# Test concurrent mutation rejection
# (Covered by test_ec_lifecycle_fake.py::test_concurrent_mutation_rejection)

# Test operation idempotency
# (Covered by test_ec_lifecycle_fake.py::test_operation_idempotency)
```

### 11. Bounded Evidence
```bash
# Test evidence retention bounds
# (Covered by test_ec_lifecycle_fake.py::test_evidence_retention_bounds)

# Test sanitized status summary
# (Covered by test_ec_lifecycle_fake.py::test_sanitized_status_summary)
```

## Running the Tests
```bash
# Run all fake-system lifecycle tests
pytest tests/test_ec_lifecycle_fake.py -v

# Run specific test categories
pytest tests/test_ec_lifecycle_fake.py -k "msi" -v
pytest tests/test_ec_lifecycle_fake.py -k "rollback" -v
pytest tests/test_ec_lifecycle_fake.py -k "reconciliation" -v
```

## Evidence Recording
```bash
# Record test results with SHA-256 binding
echo "Candidate: <candidate-name>" > evidence.txt
echo "SHA-256: <exact-sha-256>" >> evidence.txt
echo "Test Suite: Fake-System Lifecycle" >> evidence.txt
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> evidence.txt
echo "Test Results:" >> evidence.txt
pytest tests/test_ec_lifecycle_fake.py -v --tb=short >> evidence.txt
```

## Privacy Sanitization
- Remove usernames, home paths, serial numbers, UUIDs
- Remove private keys, enrollment passwords
- Remove unrelated logs
- Keep only Threshold-specific evidence
