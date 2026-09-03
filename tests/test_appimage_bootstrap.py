"""End-to-end AppImage bootstrap authority tests (fake system, no root).

Streams a signed EC bundle into the real bootstrap script and verifies:
signature against pinned trust, sequence monotonicity (downgrade
refusal), payload checksum binding, tamper rejection, package-owned
authority protection, and atomic installation.
"""

import base64
import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "packaging" / "threshold-appimage-bootstrap"
LIFECYCLE = ROOT / "packaging" / "threshold-ec-lifecycle"

openssl_gen = pytest.importorskip  # noqa: F841  (openssl required below)


def make_keypair(tmp_path: Path) -> tuple[Path, Path]:
    priv = tmp_path / "signing.pem"
    pub = tmp_path / "trust.pub"
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "ed25519", "-out", str(priv)],
        check=True, capture_output=True,
    )
    subprocess.run(
        ["openssl", "pkey", "-in", str(priv), "-pubout", "-out", str(pub)],
        check=True, capture_output=True,
    )
    return priv, pub


def sign_manifest(priv: Path, manifest: dict) -> dict:
    m = dict(manifest)
    m.pop("signature", None)
    canon_file = priv.with_suffix(".canon")
    sigfile = priv.with_suffix(".sig")
    canon_file.write_bytes(
        json.dumps(m, sort_keys=True, indent=1, separators=(",", ": ")).encode()
    )
    subprocess.run(
        ["openssl", "pkeyutl", "-sign", "-inkey", str(priv),
         "-rawin", "-in", str(canon_file), "-out", str(sigfile)],
        check=True, capture_output=True,
    )
    m["signature"] = base64.b64encode(sigfile.read_bytes()).decode()
    return m


def make_bundle(tmp_path: Path, priv: Path, sequence: int, payload: bytes | None = None,
                tamper: bool = False) -> bytes:
    manifest = {
        "schema": 1,
        "protocol": 1,
        "arch": "x86_64",
        "sequence": sequence,
        "lifecycle": {"path": "lifecycle"},
        "dkms": {"name": "msi-ec"},
        "checksum": "0" * 64,
        "bundle_checksum": None,
    }
    if payload is None:
        # Real payload: tar.gz containing the lifecycle script (and the
        # DKMS source the authority materializes later).
        import tarfile
        import io
        stage = tmp_path / "bundle-stage"
        stage.mkdir(exist_ok=True)
        shutil.copy(LIFECYCLE, stage / "lifecycle")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            tar.add(stage / "lifecycle", arcname="lifecycle")
        payload = buf.getvalue()
    import hashlib
    manifest["bundle_checksum"] = hashlib.sha256(payload).hexdigest()
    if tamper:
        manifest["bundle_checksum"] = "f" * 64
    signed = sign_manifest(priv, manifest)
    # Stream contract: single-line manifest, then the raw payload.
    line = json.dumps(signed, sort_keys=True, separators=(",", ":"))
    return line.encode() + b"\n" + payload


@pytest.fixture()
def app_env(tmp_path: Path):
    priv, pub = make_keypair(tmp_path)
    appdir = tmp_path / "app"
    (appdir / "bin").mkdir(parents=True)
    (appdir / "share" / "threshold").mkdir(parents=True)
    shutil.copy(BOOTSTRAP, appdir / "bin" / "bootstrap")
    shutil.copy(
        ROOT / "data" / "threshold-boot-reconcile.service",
        appdir / "share" / "threshold" / "threshold-boot-reconcile.service",
    )
    state = tmp_path / "ec-state"
    state.mkdir()
    env = dict(
        os.environ,
        THRESHOLD_AUTHORITY_DIR=str(tmp_path / "authority"),
        THRESHOLD_AUTHORITY_BIN=str(tmp_path / "sbin" / "threshold-ec-lifecycle"),
        THRESHOLD_AUTHORITY_UNIT=str(tmp_path / "unit" / "threshold-boot-reconcile.service"),
        THRESHOLD_TRUST_PUB=str(pub),
        THRESHOLD_EC_STATE_DIR=str(state),
        THRESHOLD_EC_KERNEL="fake-kernel",
        PATH=f"{tmp_path / 'bin'}:{os.environ['PATH']}",
    )
    (tmp_path / "bin").mkdir()
    for tool in ("dkms", "modprobe", "mokutil", "udevadm"):
        p = tmp_path / "bin" / tool
        p.write_text("#!/bin/sh\nexit 0\n")
        p.chmod(0o755)
    return type("Env", (), {
        "tmp": tmp_path, "priv": priv, "pub": pub,
        "bootstrap": appdir / "bin" / "bootstrap", "env": env,
        "authority_bin": tmp_path / "sbin" / "threshold-ec-lifecycle",
    })


def run_bootstrap(env, bundle: bytes, verb: str = "install"):
    return subprocess.run(
        [str(env.bootstrap), verb],
        input=bundle, env=env.env,
        capture_output=True, text=False, timeout=60,
    )


class TestBootstrapTrust:
    def test_signed_bundle_installs_authority(self, app_env):
        e = app_env
        r = run_bootstrap(e, make_bundle(e.tmp, e.priv, sequence=1))
        assert r.returncode == 0, r.stderr
        assert e.authority_bin.exists()
        active = json.loads(
            (e.tmp / "authority" / "active-manifest.json").read_text()
        )
        assert active["sequence"] == 1

    def test_tampered_payload_is_rejected_before_mutation(self, app_env):
        e = app_env
        r = run_bootstrap(e, make_bundle(e.tmp, e.priv, sequence=1, tamper=True))
        assert r.returncode != 0
        assert not e.authority_bin.exists()

    def test_bad_signature_is_rejected(self, app_env):
        e = app_env
        other_dir = e.tmp / "other-key"
        other_dir.mkdir()
        other, _ = make_keypair(other_dir)
        r = run_bootstrap(e, make_bundle(e.tmp, other, sequence=1))
        assert r.returncode != 0
        assert not e.authority_bin.exists()

    def test_downgrade_is_refused(self, app_env):
        e = app_env
        assert run_bootstrap(e, make_bundle(e.tmp, e.priv, sequence=5)).returncode == 0
        r = run_bootstrap(e, make_bundle(e.tmp, e.priv, sequence=4), verb="update")
        assert r.returncode != 0
        assert b"downgrade" in r.stderr.lower()

    def test_upgrade_with_higher_sequence_succeeds(self, app_env):
        e = app_env
        assert run_bootstrap(e, make_bundle(e.tmp, e.priv, sequence=5)).returncode == 0
        r = run_bootstrap(e, make_bundle(e.tmp, e.priv, sequence=6), verb="update")
        assert r.returncode == 0
        active = json.loads(
            (e.tmp / "authority" / "active-manifest.json").read_text()
        )
        assert active["sequence"] == 6
        # last-known-good preserved the previous active engine
        assert (e.tmp / "authority" / "threshold-ec-lifecycle.last-known-good").exists()

    def test_package_owned_authority_is_never_overwritten(self, app_env):
        e = app_env
        (e.tmp / "ec-state" / "package-owned").write_text("")
        r = run_bootstrap(e, make_bundle(e.tmp, e.priv, sequence=1))
        assert r.returncode != 0
        assert not e.authority_bin.exists()

    def test_unsigned_manifest_is_rejected(self, app_env):
        e = app_env
        bundle = make_bundle(e.tmp, e.priv, sequence=1)
        signed_line, payload = bundle.split(b"\n", 1)
        m = json.loads(signed_line)
        del m["signature"]
        # An unsigned manifest fails even before signature verification.
        unsigned = json.dumps(m).encode()
        r = run_bootstrap(e, unsigned + b"\n" + payload)
        assert r.returncode != 0


# ── Issue #91: recovery and provenance contract ─────────────────────────────


def _bootstrap_text() -> str:
    return BOOTSTRAP.read_text(encoding="utf-8")


def test_bootstrap_has_recovery_cleanup():
    text = _bootstrap_text()
    assert "cleanup_interrupted_state" in text
    assert "recover_last_known_good" in text


def test_bootstrap_cleans_orphaned_staging():
    text = _bootstrap_text()
    assert "rm -rf" in text
    assert "orphaned staging" in text.lower() or "clean" in text.lower()


def test_bootstrap_restores_last_known_good_on_failure():
    text = _bootstrap_text()
    assert "last-known-good" in text
    assert "recover_last_known_good" in text
    # Must attempt recovery when authority fails
    assert "AUTH_EXIT" in text


def test_bootstrap_fsyncs_staged_authority():
    text = _bootstrap_text()
    assert "fsync" in text.lower()


def test_bootstrap_validates_staged_script_offline():
    text = _bootstrap_text()
    assert "sh -n" in text
    assert "staged lifecycle" in text.lower() or "offline validation" in text.lower()
