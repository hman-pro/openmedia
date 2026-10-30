"""Injected acquisition boundaries; no real Docker/APT/download in controlled tests."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/release'))
import collect_sources as collector
import debian_acquire
import validate_release as release


def archive(path, name='pkg/LICENSE', link=None):
    with tarfile.open(path, 'w:gz') as out:
        info = tarfile.TarInfo(name)
        if link:
            info.type = tarfile.SYMTYPE; info.linkname = link; out.addfile(info)
        else:
            info.size = 7; out.addfile(info, io.BytesIO(b'license'))


@pytest.mark.parametrize('name,link', [('../escape', None), ('/absolute', None), ('pkg/link', '../../escape'), ('pkg/device', None)])
def test_unsafe_sources_rejected(tmp_path, name, link):
    path = tmp_path / 'source.tar.gz'; archive(path, name, link)
    if name == 'pkg/device':
        with tarfile.open(path, 'w:gz') as out:
            info = tarfile.TarInfo(name); info.type = tarfile.CHRTYPE; out.addfile(info)
    with pytest.raises(release.ReleaseError): release.inspect_archive(path)


def test_safe_internal_symlink_archive_is_inspectable(tmp_path):
    path = tmp_path / 'a.tar.gz'; archive(path, 'pkg/link', 'LICENSE')
    release.inspect_archive(path)


def test_debian_source_version_and_built_using():
    text = (ROOT / 'tests/fixtures/release/sources/dpkg.tsv').read_text()
    rows = collector.parse_dpkg(text, 'linux/arm64')
    assert rows[0]['version'] == '1.0-1+b1'
    assert rows[0]['source_identity'] == {'name': 'sample-source', 'version': '1.0-1'}
    assert rows[0]['incorporated_sources'] == [{'name': 'embedded', 'version': '2.0-1'}]


def test_reviewed_source_policy_covers_every_incorporated_edge():
    policy = json.loads((ROOT / 'release/source-policy.json').read_text())
    for component in policy['components']:
        for edge in component.get('incorporated_sources', []):
            matches = [c for c in policy['components'] if c.get('source_identity') == edge]
            assert len(matches) == 1, (component['name'], edge)


def test_debian_receipt_uses_isolated_https_origins(tmp_path, monkeypatch):
    payload = b'fixture'
    checksum = hashlib.sha256(payload).hexdigest()
    original_write = Path.write_text
    commands = []

    def write(path, text, *args, **kwargs):
        if str(path) == '/etc/apt/sources.list.d/openmedia-sources.sources':
            assert 'URIs: http://' not in text
            return len(text)
        return original_write(path, text, *args, **kwargs)

    def command(args):
        commands.append(args)
        if args[0] == 'dpkg-query': return 'fixture\t1\n'
        assert args[1:5] == debian_acquire.SOURCE_OPTIONS
        if args[0] == 'apt-cache':
            return f'Package: fixture\nVersion: 1\nChecksums-Sha256:\n {checksum} 7 fixture.tar.gz\n'
        if '--print-uris' in args:
            return f"'https://example.org/fixture.tar.gz' fixture.tar.gz 7 SHA256:{checksum}\n"
        return ''

    def run(args, **kwargs):
        if args[0] == 'apt-get':
            assert args[1:5] == debian_acquire.SOURCE_OPTIONS
            (kwargs['cwd'] / 'fixture.tar.gz').write_bytes(payload)

    monkeypatch.setattr(Path, 'write_text', write)
    monkeypatch.setattr(Path, 'touch', lambda *args, **kwargs: None)
    monkeypatch.setattr(debian_acquire, 'command', command)
    monkeypatch.setattr(debian_acquire.subprocess, 'run', run)
    monkeypatch.setattr(sys, 'argv', ['debian_acquire.py', '--name', 'fixture', '--version', '1',
                                    '--snapshot', '20261028T000000Z', '--output', str(tmp_path)])
    debian_acquire.main()
    receipt = json.loads((tmp_path / 'receipt.json').read_text())
    assert receipt['files'][0]['url'] == 'https://example.org/fixture.tar.gz'
    assert receipt['files'][0]['sha256'] == checksum
    assert any('--print-uris' in args for args in commands)


def test_built_using_debian_source_retains_original_notices(tmp_path, monkeypatch):
    component = {'component_id': 'embedded:unicode-data@15.0.0-1',
                 'name': 'unicode-data', 'kind': 'embedded', 'acquisition': 'debian',
                 'source_identity': {'name': 'unicode-data', 'version': '15.0.0-1'},
                 'notice_patterns': ['copyright'], 'notice_paths': [], 'build_materials': []}

    def acquire(identity, destination, *args):
        destination.mkdir(parents=True)
        source = destination / 'unicode-data.debian.tar.gz'
        archive(source, 'debian/copyright')
        return {'files': [{'name': source.name, 'sha256': release.digest(source),
                           'size': source.stat().st_size}]}

    monkeypatch.setattr(collector, 'collect_debian', acquire)
    collector._acquire_components({component['component_id']: component}, [],
                                 {'collector_image': 'fixture', 'debian_snapshot': 'fixture'},
                                 tmp_path, ROOT, 'fixture')
    assert component['coverage'] == 'complete'
    assert len(component['notice_paths']) == 1
    assert (tmp_path / component['notice_paths'][0]).read_bytes() == b'license'


def test_unknown_unmanaged_and_unlocked_python_fail_closed():
    for component in [{'kind': 'unmanaged', 'name': 'surprise', 'version': '1'}, {'kind': 'system-python', 'name': 'pip', 'version': 'unknown'}]:
        with pytest.raises(release.ReleaseError): collector.resolve_component(component, {'components': []}, {'package': []})


def test_python_sdist_is_selected_by_installed_version_and_hash():
    lock = {'package': [{'name': 'example-pkg', 'version': '1', 'sdist': {'url': 'https://files.pythonhosted.org/pkg.tar.gz', 'hash': 'sha256:' + 'a'*64, 'size': 7}}]}
    resolved = collector.resolve_component({'kind': 'application-python', 'name': 'example_pkg', 'version': '1'}, {'components': []}, lock)
    assert resolved['source_files'][0]['sha256'] == 'a'*64
    with pytest.raises(release.ReleaseError): collector.resolve_component({'kind': 'application-python', 'name': 'example_pkg', 'version': '2'}, {'components': []}, lock)


@pytest.mark.parametrize('failure', ['hash', 'interruption'])
def test_acquisition_is_atomic_and_checks_hash(tmp_path, failure):
    def download(url, target):
        target.write_bytes(b'wrong')
        if failure == 'interruption': raise InterruptedError('injected')
    target = tmp_path / 'source.tar.gz'
    with pytest.raises((release.ReleaseError, InterruptedError)):
        collector.acquire({'url': 'https://example.org/source', 'sha256': 'a'*64, 'size': 5}, target, download=download)
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_dsc_requires_every_referenced_file(tmp_path):
    dsc = 'Format: 3.0 (quilt)\nSource: sample\nVersion: 1\nChecksums-Sha256:\n ' + 'a'*64 + ' 7 sample.orig.tar.gz\n ' + 'b'*64 + ' 8 sample.debian.tar.xz\n'
    rows = collector.parse_dsc(dsc)
    assert len(rows) == 2
    assert {x['name'] for x in rows} == {'sample.orig.tar.gz', 'sample.debian.tar.xz'}
    with pytest.raises(release.ReleaseError): collector.parse_dsc(dsc.replace('sample.orig.tar.gz', '../bad'))


def test_archive_member_cannot_traverse_safe_directory_symlink(tmp_path):
    path = tmp_path / 'source.tar.gz'
    with tarfile.open(path, 'w:gz') as out:
        link = tarfile.TarInfo('pkg/link'); link.type = tarfile.SYMTYPE; link.linkname = 'inside'; out.addfile(link)
        info = tarfile.TarInfo('pkg/link/file'); info.size = 1; out.addfile(info, io.BytesIO(b'x'))
    with pytest.raises(release.ReleaseError, match='traverses'): release.inspect_archive(path)


def test_archive_cycles_and_normalized_duplicates_rejected(tmp_path):
    for cycle in (False, True):
        path = tmp_path / ('cycle.tar' if cycle else 'duplicate.tar')
        with tarfile.open(path, 'w') as out:
            for name, target in [('pkg/a','b'), ('pkg/b','a')] if cycle else [('pkg/a',None), ('./pkg/a',None)]:
                info = tarfile.TarInfo(name)
                if target: info.type = tarfile.SYMTYPE; info.linkname = target
                out.addfile(info)
        with pytest.raises(release.ReleaseError): release.inspect_archive(path)


def test_pinned_download_stops_after_expected_size_plus_one(tmp_path, monkeypatch):
    class Response(io.BytesIO):
        url = 'https://example.org/source'
        bytes_read = 0
        def read(self, size=-1):
            block = super().read(size); self.bytes_read += len(block); return block
    response = Response(b'x' * 10000)
    monkeypatch.setattr(collector, 'urlopen', lambda *args, **kwargs: response)
    material = {'url': response.url, 'sha256': 'a'*64, 'size': 7}
    with pytest.raises(release.ReleaseError): collector.acquire(material, tmp_path / 'target')
    assert not list(tmp_path.iterdir())
    assert response.bytes_read == 8


def test_unknown_executable_outside_usrlocal_is_visible_to_inventory(tmp_path, monkeypatch):
    # Run the actual probe against injected file/metadata boundaries without Docker.
    # The fixture filesystem path uses /opt, outside all original scanner roots.
    import runpy
    import subprocess
    import base64
    file = tmp_path / 'foreign'; file.write_bytes(b'\x7fELF' + b'controlled')
    original_open = Path.open; original_is_file = Path.is_file; original_read = Path.read_bytes; original_stat = Path.stat
    foreign = Path('/opt/foreign')
    monkeypatch.setattr(Path, 'open', lambda self,*a,**k: original_open(file,*a,**k) if self == foreign else original_open(self,*a,**k))
    monkeypatch.setattr(Path, 'is_file', lambda self: self == foreign)
    monkeypatch.setattr(Path, 'is_symlink', lambda self: False)
    monkeypatch.setattr(Path, 'read_bytes', lambda self: original_read(file) if self == foreign else original_read(self))
    monkeypatch.setattr(Path, 'glob', lambda *args: [])
    monkeypatch.setattr(Path, 'resolve', lambda self: self)
    monkeypatch.setattr(collector.os, 'walk', lambda *a,**k: [('/', ['opt'], []), ('/opt', [], ['foreign'])])
    def command(args, **kwargs):
        if '--python-only' in args: return '[]'
        if args[:2] == ['dpkg-query','-W']:
            return 'fixture\n' if args[-1].startswith('-f=${binary:Package}') and '\t' not in args[-1] else 'fixture\t1\tfixture\t1\t\n'
        if args[:2] == ['dpkg-query','-L']: return ''
        return 'controlled version'
    monkeypatch.setattr(subprocess, 'check_output', command)
    import importlib.metadata
    monkeypatch.setattr(importlib.metadata, 'distributions', lambda: [])
    monkeypatch.setattr(sys, 'argv', ['inventory_probe.py'])
    result = runpy.run_path(str(ROOT / 'scripts/release/inventory_probe.py'))
    assert result['unmanaged'][0]['path'] == '/opt/foreign'


@pytest.mark.parametrize('fault', ['source_version', 'missing_orig', 'wrong_patch_hash', 'success'])
def test_authenticated_debian_receipt_must_match_dsc_and_all_references(tmp_path, monkeypatch, fault):
    identity = {'name':'sample','version':'1.0-1'}
    text = 'Source: sample\nVersion: 1.0-1\nChecksums-Sha256:\n ' + 'a'*64 + ' 7 sample.orig.tar.gz\n ' + 'b'*64 + ' 8 sample.debian.tar.xz\n'
    if fault == 'source_version': text = text.replace('Version: 1.0-1','Version: 1.0-1+b1')
    (tmp_path/'sample.dsc').write_text(text)
    files = [{'name':'sample.dsc','sha256':'c'*64,'size':len(text)}, {'name':'sample.orig.tar.gz','sha256':'a'*64,'size':7},{'name':'sample.debian.tar.xz','sha256':'b'*64,'size':8}]
    if fault == 'missing_orig': files.pop(1)
    if fault == 'wrong_patch_hash': files[-1]['sha256'] = 'd'*64
    if fault == 'success': collector.validate_debian_receipt({'files':files}, tmp_path, identity)
    else:
        with pytest.raises(release.ReleaseError): collector.validate_debian_receipt({'files':files}, tmp_path, identity)
