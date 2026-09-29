#!/usr/bin/env python3
"""Seed xbps-src with the canonical archive; never fetch a version-tag fallback."""
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import tarfile


def prepare(source: Path, archive: Path, checkout: Path) -> None:
    template = (source / 'packaging/void/template').read_text()
    version = re.search(r'^version=([0-9.]+)$', template, re.M).group(1)
    expected = f'Threshold-{version}.tar.gz'
    if archive.name != expected:
        raise ValueError(f'Expected {expected}')
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or path.parts[0] != f'Threshold-{version}':
                raise ValueError('Archive has an unexpected source root')
    target = checkout / 'srcpkgs/threshold'
    if target.exists():
        raise ValueError('Refusing to replace an existing build recipe')
    shutil.copytree(source / 'packaging/void', target)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    template = re.sub(r'^distfiles=.*$', f'distfiles="https://canonical-source.invalid/{expected}"', template, flags=re.M)
    template = re.sub(r'^checksum=.*$', f'checksum={digest}', template, flags=re.M)
    template += f'\nwrksrc="Threshold-{version}"\n'
    (target / 'template').write_text(template)
    cache = checkout / f'hostdir/sources/threshold-{version}'
    cache.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(archive, cache / expected)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('archive', type=Path)
    parser.add_argument('checkout', type=Path)
    args = parser.parse_args()
    prepare(args.source, args.archive, args.checkout)
