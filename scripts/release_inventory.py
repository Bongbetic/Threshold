#!/usr/bin/env python3
"""Construct and validate immutable release inventories and physical acceptance."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re


SHA = re.compile(r"[0-9a-f]{64}")
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
PHYSICAL_CHECKS = {
    "installation", "live_ec", "reboot_reconciliation", "machine_policy",
    "secure_boot", "failed_kernel_build", "known_good_boot", "named_kernel_repair",
    "subsequent_verification", "safe_removal",
}
VOID_DESKTOP_CHECKS = {
    "native_wayland", "dms_appearance", "tiling", "normal_size_clipping",
    "watcher_restart", "portal_restart", "scaling", "pointer_controls",
    "notification_area_menu", "activation_token",
}
PRIVACY = re.compile(
    r"/home/(?!<user>/)[^/\s]+/|/root/|serial=[A-Za-z0-9]+|UUID=[0-9a-fA-F-]+|"
    r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|ssh-rsa "
)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fail(message):
    raise ValueError(message)


def names_for(version, names):
    patterns = [
        rf"threshold_{re.escape(version)}-\d+_amd64\.deb",
        rf"threshold-{re.escape(version)}-.*\.noarch\.rpm",
        rf"threshold-{re.escape(version)}-.*\.src\.rpm",
        rf"Threshold-{re.escape(version)}\.tar\.gz",
        rf"threshold-{re.escape(version)}_1\.x86_64\.xbps",
        "x86_64-repodata", "void-build.json", "void-dependencies.txt",
    ]
    expected = set()
    for pattern in patterns:
        matches = [name for name in names if re.fullmatch(pattern, name)]
        if len(matches) != 1:
            fail(f'Expected exactly one asset matching {pattern}')
        expected.add(matches[0])
    # AppImage remains unavailable until the existing EC trust-key packaging is resolved.
    appimage = f'Threshold-{version}-x86_64.AppImage'
    if appimage in names:
        expected.add(appimage)
    if set(names) != expected:
        fail('Unexpected release asset names')
    return expected


def manifest(directory, version, revision, identity):
    names = [p.name for p in directory.iterdir() if p.is_file()]
    names_for(version, names)
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        fail('Source revision must be a full commit ID')
    result = {
        'version': version, 'source_revision': revision, 'build_identity': identity,
        'verification': {
            'package_jobs': 'required before draft assembly',
            'physical_evidence': 'required at promotion; not established by package CI',
            'desktop_evidence': 'required at promotion; staged observations are not acceptance',
        },
        'candidates': {name: {'sha256': digest(directory / name), 'source_revision': revision}
                       for name in sorted(names)},
    }
    source_name = f'Threshold-{version}.tar.gz'
    provenance = json.loads((directory / 'void-build.json').read_text())
    if provenance['source_sha256'] != result['candidates'][source_name]['sha256']:
        fail('Void build used a different canonical source archive')
    (directory / 'release-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    names.append('release-manifest.json')
    (directory / 'SHA256SUMS').write_text(''.join(
        f'{digest(directory / name)}  {name}\n' for name in sorted(names)))


def verify(directory, version, revision):
    inventory = {}
    for line in (directory / 'SHA256SUMS').read_text().splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9_.-]*)', line)
        if not match or match[2] in inventory:
            fail('Malformed or duplicate checksum entry')
        inventory[match[2]] = match[1]
    actual = {p.name for p in directory.iterdir()}
    allowed = set(inventory) | {'SHA256SUMS'}
    if 'SHA256SUMS.asc' in actual:
        allowed.add('SHA256SUMS.asc')
    if actual != allowed or 'release-manifest.json' not in inventory:
        fail('Draft asset inventory differs from checksums')
    for name, checksum in inventory.items():
        path = directory / name
        if path.is_symlink() or not path.is_file() or digest(path) != checksum:
            fail(f'Checksum mismatch: {name}')
    data = json.loads((directory / 'release-manifest.json').read_text())
    if data['version'] != version or data['source_revision'] != revision:
        fail('Manifest version/source does not match the selected tag')
    names_for(version, data['candidates'])
    if set(data['candidates']) != set(inventory) - {'release-manifest.json'}:
        fail('Manifest and checksum inventories differ')
    for name, entry in data['candidates'].items():
        if entry['sha256'] != inventory[name] or entry['source_revision'] != revision:
            fail(f'Manifest identity mismatch: {name}')
    provenance = json.loads((directory / 'void-build.json').read_text())
    if provenance['source_sha256'] != inventory[f'Threshold-{version}.tar.gz']:
        fail('Void source archive mismatch')
    return data


def physical(directory, report_path, version, revision, now=None):
    data = verify(directory, version, revision)
    text = report_path.read_text()
    if PRIVACY.search(text):
        fail('Acceptance report contains private information')
    report = json.loads(text)
    if report.get('source_revision') != revision:
        fail('Acceptance source revision mismatch')
    now = now or datetime.now(timezone.utc)
    by_platform = {}
    for record in report['records']:
        name = record['candidate']
        if name not in data['candidates'] or record['sha256'] != data['candidates'][name]['sha256']:
            fail('Acceptance candidate hash mismatch')
        if record.get('system') != 'MSI Thin A15 B7UCX' or record.get('physical') is not True:
            fail('Real MSI hardware evidence is required; simulation is not acceptance')
        if not record.get('kernel') or not record.get('os'):
            fail('Missing platform versions')
        platform = record['platform']
        if platform in by_platform:
            fail('Duplicate physical platform record')
        required = set(PHYSICAL_CHECKS)
        if platform == 'void-x86_64-glibc':
            if not name.endswith('.x86_64.xbps'):
                fail('Void evidence must name the XBPS')
            required |= VOID_DESKTOP_CHECKS
        elif platform == 'existing-desktops':
            if not name.endswith(('.deb', '.rpm', '.AppImage')) or name.endswith('.src.rpm'):
                fail('Existing desktop evidence must name an installable candidate')
            required |= {'kde_plasma_wayland', 'xfce'}
        else:
            fail('Unexpected physical platform')
        checks = record['checks']
        if not required <= set(checks):
            fail(f'Missing physical checks: {sorted(required - set(checks))}')
        for key in required:
            check = checks[key]
            timestamp = datetime.strptime(check['timestamp'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            if not now - timedelta(days=7) <= timestamp <= now:
                fail(f'Stale or future evidence: {key}')
            if check['result'] != 'pass' or not check.get('details', '').strip():
                fail(f'Unsuccessful or unexplained physical check: {key}')
            # Evidence assets live alongside the report in a separately committed evidence ref.
            asset = Path(check['asset'])
            if asset.is_absolute() or '..' in asset.parts or not asset.parts:
                fail('Unsafe evidence asset path')
            root = report_path.parent.resolve()
            resolved = (root / asset).resolve()
            if not resolved.is_relative_to(root) or not resolved.is_file():
                fail(f'Missing evidence asset: {asset}')
            if not SHA.fullmatch(check['asset_sha256']) or digest(resolved) != check['asset_sha256']:
                fail(f'Evidence asset hash mismatch: {asset}')
            if resolved.suffix in {'.txt', '.log', '.json', '.md'} and PRIVACY.search(resolved.read_text()):
                fail(f'Unsanitized evidence asset: {asset}')
        by_platform[platform] = record
    if set(by_platform) != {'void-x86_64-glibc', 'existing-desktops'}:
        fail('Missing Void or existing desktop physical acceptance')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['manifest', 'verify', 'physical'])
    parser.add_argument('directory', type=Path)
    parser.add_argument('--version', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--identity', default='local')
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'manifest':
            manifest(args.directory, args.version, args.revision, args.identity)
        elif args.action == 'verify':
            verify(args.directory, args.version, args.revision)
        else:
            if args.evidence is None:
                fail('Physical evidence report is required')
            physical(args.directory, args.evidence, args.version, args.revision)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'Release validation failed: {error}\n')
