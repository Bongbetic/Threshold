"""Release gating rejects corrupt candidates and missing or misbound evidence."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'release_inventory', ROOT / 'scripts/release_inventory.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
source_spec = importlib.util.spec_from_file_location(
    'prepare', ROOT / 'scripts/prepare-void-source.py')
source = importlib.util.module_from_spec(source_spec)
source_spec.loader.exec_module(source)
REVISION = 'a' * 40
VERSION = '2.0.2'


@pytest.fixture
def draft(tmp_path):
    folder = tmp_path / 'draft'
    folder.mkdir()
    for name in ['threshold_2.0.2-1_amd64.deb', 'threshold-2.0.2-1.fc44.noarch.rpm',
                 'threshold-2.0.2-1.fc44.src.rpm', 'Threshold-2.0.2.tar.gz',
                 'threshold-2.0.2_1.x86_64.xbps', 'x86_64-repodata', 'void-dependencies.txt']:
        (folder / name).write_text(name)
    (folder / 'void-build.json').write_text(json.dumps({
        'source_sha256': release.digest(folder / 'Threshold-2.0.2.tar.gz'),
    }))
    (folder / 'void-verification.json').write_text(json.dumps({
        'candidate': 'threshold-2.0.2_1.x86_64.xbps',
        'sha256': release.digest(folder / 'threshold-2.0.2_1.x86_64.xbps'),
        'result': 'pass', 'physical': False,
        'checks': ['installation', 'owned_payload', 'runtime_typelibs', 'schema',
                   'disabled_service', 'reinstall_policy', 'removal_policy',
                   'foreign_probe_preserved'],
    }))
    release.manifest(folder, VERSION, REVISION, 'test-build')
    return folder


def test_verifies_complete_draft(draft):
    assert release.verify(draft, VERSION, REVISION)['build_identity'] == 'test-build'


@pytest.mark.parametrize('mutation', ['corrupt', 'missing', 'extra', 'manifest', 'duplicate'])
def test_rejects_asset_tampering(draft, mutation):
    package = draft / 'threshold-2.0.2_1.x86_64.xbps'
    if mutation == 'corrupt':
        package.write_text('different build')
    elif mutation == 'missing':
        package.unlink()
    elif mutation == 'extra':
        (draft / 'other.xbps').write_text('unexpected')
    elif mutation == 'manifest':
        (draft / 'release-manifest.json').write_text('{}')
    else:
        sums = draft / 'SHA256SUMS'
        sums.write_text(sums.read_text() * 2)
    with pytest.raises(ValueError):
        release.verify(draft, VERSION, REVISION)


def test_rejects_different_source_revision(draft):
    with pytest.raises(ValueError, match='source'):
        release.verify(draft, VERSION, 'b' * 40)


def acceptance(draft, tmp_path):
    # Synthetic fixtures exercise validation only; never write under repository evidence/.
    asset = tmp_path / 'probe.txt'
    asset.write_text('Synthetic unit-test fixture')
    records = []
    for platform, candidate, extra in [
        ('void-x86_64-glibc', 'threshold-2.0.2_1.x86_64.xbps', release.VOID_DESKTOP_CHECKS),
        ('existing-desktops', 'threshold_2.0.2-1_amd64.deb', {'kde_plasma_wayland', 'xfce'}),
    ]:
        records.append({
            'platform': platform, 'candidate': candidate,
            'sha256': release.digest(draft / candidate), 'physical': True,
            'system': 'MSI Thin A15 B7UCX', 'kernel': 'test-kernel', 'os': 'test-os',
            'checks': {name: {
                'timestamp': '2026-09-29T12:00:00Z', 'result': 'pass',
                'details': 'Synthetic unit-test fixture', 'asset': 'probe.txt',
                'asset_sha256': release.digest(asset),
            } for name in release.PHYSICAL_CHECKS | extra},
        })
    return {'source_revision': REVISION, 'records': records}


@pytest.mark.parametrize('fault', [None, 'missing', 'hash', 'stale', 'future', 'bad_date',
                                   'simulation', 'failure', 'asset', 'privacy', 'details'])
def test_physical_gate_fails_closed(draft, tmp_path, fault):
    report = acceptance(draft, tmp_path)
    record = report['records'][0]
    check = record['checks']['installation']
    if fault == 'missing':
        del record['checks']['reboot_reconciliation']
    elif fault == 'hash':
        record['sha256'] = '0' * 64
    elif fault == 'stale':
        check['timestamp'] = '2026-09-01T12:00:00Z'
    elif fault == 'future':
        check['timestamp'] = '2026-10-01T12:00:00Z'
    elif fault == 'bad_date':
        check['timestamp'] = 'yesterday'
    elif fault == 'simulation':
        record['physical'] = False
    elif fault == 'failure':
        check['result'] = 'fail'
    elif fault == 'asset':
        check['asset'] = '../outside.txt'
    elif fault == 'privacy':
        check['details'] = '/home/person/private'
    elif fault == 'details':
        check['details'] = ''
    path = tmp_path / 'acceptance.json'
    path.write_text(json.dumps(report))
    now = datetime(2026, 9, 29, 13, tzinfo=timezone.utc)
    if fault is None:
        assert release.physical(draft, path, VERSION, REVISION, now)['records']
    else:
        with pytest.raises(ValueError):
            release.physical(draft, path, VERSION, REVISION, now)


def test_source_cache_uses_supplied_archive_not_tag(tmp_path):
    checkout = tmp_path / 'void-packages'
    source_tree = tmp_path / 'source'
    template = source_tree / 'packaging/void/template'
    template.parent.mkdir(parents=True)
    template.write_text('version=2.0.2\ndistfiles="https://old.invalid/tag"\nchecksum=old\n')
    content = tmp_path / 'content'
    content.write_text('new source')
    archive = tmp_path / 'Threshold-2.0.2.tar.gz'
    with tarfile.open(archive, 'w:gz') as tar:
        tar.add(content, arcname='Threshold-2.0.2/new-file')
    source.prepare(source_tree, archive, checkout)
    prepared = (checkout / 'srcpkgs/threshold/template').read_text()
    assert 'https://old.invalid' not in prepared
    assert f'checksum={release.digest(archive)}' in prepared
    cache = checkout / 'hostdir/sources/threshold-2.0.2/Threshold-2.0.2.tar.gz'
    assert cache.read_bytes() == archive.read_bytes()
    with pytest.raises(ValueError, match='replace'):
        source.prepare(source_tree, archive, checkout)
