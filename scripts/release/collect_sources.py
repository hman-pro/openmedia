#!/usr/bin/env python3
"""Collect matching sources from actual runtime inventories; standard library only.

Network acquisition is confined to collect, while inventory runs the image offline.
APT authenticates source indexes inside the pinned collector. Unknown components and
unreviewed embedded source edges fail publication, never become implicit exceptions.
"""
from __future__ import annotations
import argparse
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
from urllib.request import urlopen

from validate_release import (ReleaseError, require, read_json, write_json, digest, safe_path,
                              inspect_archive, image_config, validate_sources, PLATFORMS, run)

HERE = Path(__file__).resolve().parent


def normalize(name): return re.sub(r'[-_.]+', '-', name).lower()


def parse_dpkg(text, platform):
    result = []
    for row in text.splitlines():
        fields = row.split('\t'); require(len(fields) == 5, 'Malformed dpkg inventory')
        binary, version, source, source_version, built_using = fields
        require(all((binary, version, source, source_version)), 'Missing Debian source identity')
        edges = []
        if built_using:
            for edge in built_using.split(','):
                match = re.fullmatch(r'\s*([a-z0-9][a-z0-9+.-]*) \(= ([^\s()]+)\)\s*', edge)
                require(match, 'Malformed Debian Built-Using')
                edges.append({'name': match[1], 'version': match[2]})
        result.append({'component_id': 'debian:' + binary.split(':')[0] + '@' + version,
                       'kind': 'debian', 'name': binary.split(':')[0], 'version': version,
                       'architectures': [platform], 'license': 'Debian package copyright and common-license texts',
                       'source_identity': {'name': source, 'version': source_version},
                       'incorporated_sources': edges})
    return result


def inventory(image, platform, output):
    require(platform in PLATFORMS, 'Unsupported inventory platform')
    config_id, config = image_config(image)
    require(config['os'] + '/' + config['architecture'] == platform, 'Inventory architecture mismatch')
    labels = config.get('config', {}).get('Labels', {})
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    raw = json.loads(run(['docker', 'run', '--rm', '--network', 'none', '--read-only', '--cap-drop', 'ALL', '--cap-add', 'DAC_READ_SEARCH',
                         '--security-opt', 'no-new-privileges', '--user', '0:0',
                         '--mount', 'type=bind,src=' + str(HERE) + ',dst=/probe,readonly',
                         '--entrypoint', '/usr/local/bin/python', image, '/probe/inventory_probe.py']))
    for tool, prefix in [('python', 'Python 3.13.15'), ('uv', 'uv 0.12.15'), ('uvx', 'uvx 0.12.15'), ('deno', 'deno 2.9.6')]:
        require(raw['tool_versions'][tool].splitlines()[0].startswith(prefix), 'Unreviewed actual unmanaged tool version')
    policy_path = HERE.parents[1] / 'release/source-policy.json'
    notice_policy = read_json(policy_path)['runtime_notice_bundle']
    notice_data = raw['notices'].get(notice_policy['path'])
    require(notice_data and hashlib.sha256(base64.b64decode(notice_data)).hexdigest() == notice_policy['sha256'], 'Missing/mismatched installed unmanaged notice bundle')
    components = parse_dpkg(raw['dpkg'], platform)
    notice_root = output / 'notices'; notice_root.mkdir(exist_ok=True)
    def retain(notices):
        result = []
        for original, data in notices.items():
            name = 'notices/' + original.lstrip('/')
            safe_path(name); path = output / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(data, validate=True)); result.append(name)
        return result
    all_notices = retain(raw['notices'])
    for component in components:
        name = 'notices/usr/share/doc/' + component['name'] + '/copyright'
        # Debian documentation symlinks were dereferenced by the probe.
        component['notice_paths'] = [name] if name in all_notices else []
    for key, kind in [('application_python', 'application-python'), ('system_python', 'system-python')]:
        for item in raw[key]:
            components.append({'component_id': kind + ':' + normalize(item['name']) + '@' + item['version'],
                               'kind': kind, 'name': normalize(item['name']), 'version': item['version'],
                               'architectures': [platform], 'license': item['license'], 'notice_paths': retain(item['notices']),
                               'source_identity': {'name': normalize(item['name']), 'version': item['version']}, 'incorporated_sources': []})
    mapping = {'/usr/local/bin/uv': ('uv', '0.12.15'), '/usr/local/bin/uvx': ('uvx', '0.12.15'),
               '/usr/local/bin/deno': ('deno', '2.9.6')}
    binaries = {}
    for item in raw['unmanaged_files']:
        path = item['path']
        if path == '/usr/sbin/policy-rc.d': name, version = 'debuerreotype-policy-rc.d', item['sha256']
        elif path in mapping: name, version = mapping[path]
        elif path in ('/usr/local/bin/idle3.13', '/usr/local/bin/pydoc3.13', '/usr/local/bin/python3.13-config') or path.startswith('/usr/local/lib/python3.13/') or path.startswith('/usr/local/lib/libpython3') or (path.startswith('/usr/local/lib/python3.13/config-') and path.endswith('/python.o')) or path == '/usr/local/bin/python3.13':
            name, version = 'cpython', '3.13.15'
        else: name, version = 'unknown:' + path, 'unknown'
        binaries.setdefault((name, version), []).append(item)
    for (name, version), files in binaries.items():
        components.append({'component_id': 'unmanaged:' + name + '@' + version, 'kind': 'unmanaged', 'name': name,
                           'version': version, 'architectures': [platform], 'binary_files': files,
                           'license': 'Source policy and full embedded notices', 'notice_paths': ['notices' + notice_policy['path']],
                           'source_identity': {'name': name, 'version': version}, 'incorporated_sources': []})
    value = {'schema_version': 1, 'platform': platform, 'image_config_id': config_id,
             'version': labels.get('org.opencontainers.image.version'), 'source_revision': labels.get('org.opencontainers.image.revision'),
             'tool_versions': raw['tool_versions'], 'components': components, 'common_notices': all_notices}
    write_json(output / ('inventory-' + platform.split('/')[1] + '.json'), value)
    return value


def resolve_component(component, policy, lock):
    result = copy.deepcopy(component); kind = component['kind']
    matches = [x for x in policy.get('components', []) if x.get('name') == component['name'] and x.get('version') == component['version'] and x.get('kind') == kind]
    if kind == 'application-python' and component['name'] != 'openmedia':
        locked = [p for p in lock.get('package', []) if normalize(p['name']) == normalize(component['name']) and p.get('version') == component['version']]
        require(len(locked) == 1 and locked[0].get('sdist'), 'Installed Python distribution has no exact locked sdist')
        sdist = locked[0]['sdist']; require(sdist['hash'].startswith('sha256:'), 'Unsupported sdist checksum')
        result['source_files'] = [{'url': sdist['url'], 'sha256': sdist['hash'][7:], 'size': sdist['size'], 'role': 'sdist'}]
        result['build_materials'] = ['build/uv.lock', 'build/pyproject.toml', 'build/Dockerfile']
        return result
    require(len(matches) == 1, 'Unreviewed installed component: ' + component['name'])
    reviewed = matches[0]
    if kind == 'debian':
        require(component['source_identity'] == reviewed['source_identity'], 'Unreviewed Debian source version')
        result.update(source_files=[], build_materials=['build/Dockerfile'])
    else:
        if kind == 'unmanaged':
            approved = reviewed.get('binary_checksums', {})
            for platform in component['architectures']:
                actual = {f['path']: f['sha256'] for f in component['binary_files']}
                require(approved.get(platform) == actual, 'Unreviewed unmanaged binary bytes')
        for key in ('source_files', 'build_materials', 'incorporated_sources'):
            require(key in reviewed, 'Missing reviewed source policy field'); result[key] = copy.deepcopy(reviewed[key])
        require(reviewed.get('embedded_review') == 'complete', 'Embedded-source closure has not been reviewed')
        result['license'] = reviewed['license']
        result['notice_patterns'] = reviewed.get('notice_patterns', [])
    return result


def download_url(url, target, expected_size):
    require(url.startswith('https://'), 'Source acquisition requires HTTPS')
    with urlopen(url, timeout=120) as response, target.open('wb') as out:
        require(response.url.startswith('https://'), 'Insecure source redirect')
        remaining = expected_size + 1
        while remaining:
            block = response.read(min(1024 * 1024, remaining))
            if not block: break
            out.write(block); remaining -= len(block)


def acquire(material, target, download=download_url):
    target = Path(target); target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        require(digest(target) == material['sha256'] and target.stat().st_size == material['size'], 'Cached source checksum mismatch')
        return target
    temporary = target.with_name(target.name + '.partial')
    try:
        if download is download_url: download(material['url'], temporary, material['size'])
        else: download(material['url'], temporary)
        require(digest(temporary) == material['sha256'] and temporary.stat().st_size == material['size'], 'Acquired source checksum mismatch')
        if tarfile.is_tarfile(temporary) or zipfile_is(temporary): inspect_archive(temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def zipfile_is(path):
    import zipfile
    return zipfile.is_zipfile(path)


def parse_dsc(text):
    # Both apt-cache showsrc and clear-signed .dsc use Debian control continuations.
    result = []; active = False
    for line in text.splitlines():
        if line == 'Checksums-Sha256:': active = True; continue
        if active and line.startswith(' '):
            parts = line.split(); require(len(parts) == 3, 'Malformed DSC checksum row')
            checksum, size, name = parts; safe_path(name)
            require('/' not in name and re.fullmatch('[a-f0-9]{64}', checksum) and size.isdigit() and int(size) > 0, 'Invalid DSC material')
            result.append({'name': name, 'sha256': checksum, 'size': int(size)})
        elif active: break
    require(bool(result), 'Missing authenticated source checksums')
    return result


def collect_debian(identity, destination, collector_image, snapshot, container=None, root=None):
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=True)
    # No upstream build code is run. APT authenticates metadata and every source file;
    # source archive paths/types are inspected again on the host before packaging.
    snapshots = snapshot if isinstance(snapshot, list) else [snapshot]
    snapshot_args = [argument for value in snapshots for argument in ('--snapshot', value)]
    existing = destination / 'receipt.json'
    if existing.exists():
        receipt = read_json(existing)
        require(receipt['source_identity'] == identity, 'Cached Debian source identity mismatch')
        for item in receipt['files']:
            require(digest(destination / item['name']) == item['sha256'], 'Cached Debian source checksum mismatch')
        validate_debian_receipt(receipt, destination, identity)
        validate_debian_unpack(destination, collector_image, container, root)
        return receipt
    command = ['docker', 'run', '--rm', '--user', '0:0',
               '--mount', 'type=bind,src=' + str(destination.resolve()) + ',dst=/output',
               '--mount', 'type=bind,src=' + str(HERE) + ',dst=/collector,readonly',
               collector_image, 'python', '/collector/debian_acquire.py', '--name', identity['name'], '--version', identity['version']] + snapshot_args
    if container:
        relative = destination.resolve().relative_to(Path(root).resolve())
        command = ['docker', 'exec', container, 'python', '/collector/debian_acquire.py', '--name', identity['name'], '--version', identity['version'], '--output', '/output/' + str(relative)] + snapshot_args
    run(command)
    receipt = read_json(destination / 'receipt.json')
    require(receipt['source_identity'] == identity, 'Wrong Debian source receipt')
    for item in receipt['files']:
        path = destination / item['name']; require(digest(path) == item['sha256'] and path.stat().st_size == item['size'], 'Debian source checksum mismatch')
        if tarfile.is_tarfile(path): inspect_archive(path)
    validate_debian_receipt(receipt, destination, identity)
    validate_debian_unpack(destination, collector_image, container, root)
    return receipt



def validate_debian_unpack(destination, collector_image, container=None, root=None):
    destination = Path(destination).resolve()
    marker = destination / 'unpack-validation.json'
    if marker.exists(): return
    if container:
        relative = destination.relative_to(Path(root).resolve())
        command = ['docker', 'exec', container, 'python', '/collector/debian_unpack.py', '/output/' + str(relative)]
    else:
        command = ['docker', 'run', '--rm', '--network', 'none', '--mount', 'type=bind,src=' + str(destination) + ',dst=/input,readonly', '--mount', 'type=bind,src=' + str(HERE) + ',dst=/collector,readonly', collector_image, 'python', '/collector/debian_unpack.py', '/input']
    run(command)
    write_json(marker, {'result': 'pass', 'method': 'authenticated hashes, safe archive inspection, standard dpkg-source extraction; no build hooks'})

def validate_debian_receipt(receipt, destination, identity):
    files = {x['name']: x for x in receipt['files']}
    dsc_names = [name for name in files if name.endswith('.dsc')]
    require(len(dsc_names) == 1, 'Missing unique Debian source descriptor')
    text = (Path(destination) / dsc_names[0]).read_text().split('-----BEGIN PGP SIGNATURE-----', 1)[0]
    require(re.findall(r'^Source: (.+)$', text, re.M) == [identity['name']] and re.findall(r'^Version: (.+)$', text, re.M) == [identity['version']], 'Debian descriptor source/version mismatch')
    for reference in parse_dsc(text):
        require(reference['name'] in files and files[reference['name']]['sha256'] == reference['sha256'] and files[reference['name']]['size'] == reference['size'], 'Missing/mismatched DSC-referenced material')


def retain_archive_notices(path, output, component):
    patterns = [x.lower() for x in component.get('notice_patterns', [])]
    if not patterns: return
    retained = []
    source_digest = None
    if tarfile.is_tarfile(path):
        with tarfile.open(path, 'r:*') as source:
            for member in source:
                if member.isfile() and any(p in member.name.lower() for p in patterns):
                    safe_path(member.name)
                    if source_digest is None: source_digest = digest(path)
                    target = output / 'notices' / 'sources' / source_digest / member.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.extractfile(member).read())
                    retained.append(str(target.relative_to(output)))
    component.setdefault('notice_paths', []).extend(retained)


def package_parts(output, components, max_size=1024**3):
    files = sorted({f['path'] for c in components for f in c['source_files']} | {p for c in components for p in c['build_materials']})
    notices = sorted({p for c in components for p in c['notice_paths']})
    files = [p for p in files if p not in notices]
    groups = []; group = []; size = 0
    for name in files:
        length = (output / name).stat().st_size
        require(length <= max_size, 'Source material exceeds logical part size; reviewed split required')
        if group and size + length > max_size: groups.append(group); group = []; size = 0
        group.append(name); size += length
    if group: groups.append(group)
    result = []
    notices = sorted({p for c in components for p in c['notice_paths']})
    for name, members in [('sources-%03d.tar.gz' % (i+1), members) for i, members in enumerate(groups)] + [('notices.tar.gz', notices)]:
        path = output / name
        import gzip
        def metadata(info):
            info.uid = info.gid = 0; info.uname = info.gname = ''; info.mtime = 0; info.mode = 0o644
            return info
        with path.open('wb') as raw, gzip.GzipFile(fileobj=raw, filename='', mode='wb', mtime=0) as compressed, tarfile.open(fileobj=compressed, mode='w') as archive:
            for member in members: archive.add(output / member, arcname=member, recursive=False, filter=metadata)
        inspect_archive(path)
        result.append({'name': name, 'sha256': digest(path), 'size': path.stat().st_size})
    return result


def collect(inventory_files, policy, lock, output, repository):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    repository = Path(repository).resolve()
    for name in ('Dockerfile', 'uv.lock', 'pyproject.toml', 'THIRD_PARTY_NOTICES.md', 'LICENSE', 'release/Collector.Dockerfile', 'release/source-policy.json', '.dockerignore', 'release/runtime-notices.txt.gz', 'release/runtime-notices.provenance.json'):
        destination = output / 'build' / Path(name).name; destination.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(repository / name, destination)
    inventories = [read_json(p) for p in inventory_files]
    write_json(output / 'source-manifest.json', {'schema_version': 1, 'inventories': inventories, 'components': [{**copy.deepcopy(c), 'coverage': 'missing', 'source_files': [], 'build_materials': []} for i in inventories for c in i['components']]})
    require(len(inventories) == 2 and {i['platform'] for i in inventories} == PLATFORMS, 'Both native inventories required')
    require(len({i['source_revision'] for i in inventories}) == 1 and len({i['version'] for i in inventories}) == 1, 'Stale platform inventories')
    components = {}
    for path, inventory_value in zip(inventory_files, inventories):
        shutil.copyfile(path, output / Path(path).name)
        notice_dir = Path(path).parent / 'notices'
        require(notice_dir.is_dir(), 'Missing actual-image notices')
        # Per-platform notices must agree byte-for-byte when paths are shared.
        for source in notice_dir.rglob('*'):
            if source.is_file():
                target = output / 'notices' / source.relative_to(notice_dir); target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists(): require(digest(target) == digest(source), 'Conflicting cross-platform notice bytes')
                else: shutil.copyfile(source, target)
        for actual in inventory_value['components']:
            write_json(output / 'collection-progress.json', {'component_id': re.sub(r'[^A-Za-z0-9.:+_@-]', '?', actual['component_id'])[:160], 'coverage': 'missing', 'stage': 'policy-resolution'})
            resolved = resolve_component(actual, policy, lock)
            key = resolved['component_id']
            if key in components:
                require(components[key]['source_identity'] == resolved['source_identity'], 'Conflicting component identities')
                components[key]['architectures'] = sorted(set(components[key]['architectures'] + resolved['architectures']))
            else: components[key] = resolved
    # Debian Built-Using edges are independent source identities, including packages
    # absent from the runtime's binary package set.
    pending = list(components.values())
    while pending:
        parent = pending.pop()
        for edge in parent['incorporated_sources']:
            existing = next((c for c in components.values() if c['source_identity'] == edge), None)
            if existing is not None:
                existing['architectures'] = sorted(set(existing['architectures'] + parent['architectures']))
                continue
            approved = [x for x in policy['components'] if x.get('source_identity') == edge]
            require(len(approved) == 1, 'Unreviewed incorporated source edge')
            reviewed = approved[0]; key = 'embedded:' + edge['name'] + '@' + edge['version']
            value = {'component_id': key, 'kind': 'embedded', 'name': edge['name'], 'version': edge['version'],
                     'architectures': list(parent['architectures']), 'notice_paths': [], 'source_identity': edge}
            for field in ('license', 'source_files', 'build_materials', 'incorporated_sources', 'notice_patterns', 'acquisition'):
                if field in reviewed: value[field] = copy.deepcopy(reviewed[field])
            require(reviewed.get('embedded_review') == 'complete', 'Unreviewed embedded source closure')
            components[key] = value; pending.append(value)
    container = run(['docker', 'run', '--detach', '--user', '0:0', '--mount', 'type=bind,src=' + str(output.resolve()) + ',dst=/output', '--mount', 'type=bind,src=' + str(HERE) + ',dst=/collector,readonly', policy['collector_image'], 'sleep', 'infinity']).strip()
    try:
        _acquire_components(components, inventories, policy, output, repository, container)
    finally:
        run(['docker', 'rm', '--force', container])
    result = {'schema_version': 1, 'inventories': inventories, 'components': list(components.values())}
    auxiliary = {p for c in result['components'] for p in c['notice_paths'] + c['build_materials']}
    result['auxiliary_files'] = {p: {'sha256': digest(output / p), 'size': (output / p).stat().st_size} for p in sorted(auxiliary)}
    write_json(output / 'collection-progress.json', {'coverage': 'missing', 'stage': 'source-packaging'})
    result['parts'] = package_parts(output, result['components'], policy.get('part_size', 1024**3))
    write_json(output / 'source-manifest.json', result)
    write_json(output / 'collection-progress.json', {'coverage': 'missing', 'stage': 'source-bundle-validation'})
    validate_sources(output)
    write_json(output / 'collection-progress.json', {'coverage': 'complete', 'stage': 'source-bundle-validation', 'result': 'pass', 'components': len(components)})
    return result


def _acquire_components(components, inventories, policy, output, repository, container):
    for component in components.values():
        print('Collect source component: ' + re.sub(r'[^A-Za-z0-9.:+_@-]', '?', component['component_id'])[:160], flush=True)
        write_json(output / 'collection-progress.json', {'component_id': component['component_id'], 'coverage': 'missing', 'stage': 'acquisition-and-notices'})
        if component['kind'] == 'debian' or component.get('acquisition') == 'debian':
            identity = component['source_identity']
            location = 'materials/debian/' + identity['name'] + '/' + re.sub('[^A-Za-z0-9.+_-]', '_', identity['version'])
            receipt = collect_debian(identity, output / location, policy['collector_image'], policy.get('debian_snapshots', [policy['debian_snapshot']]), container, output)
            component['source_files'] = [{**x, 'path': location + '/' + x['name'], 'role': 'debian-source'} for x in receipt['files']]
            component['build_materials'].extend([location + '/receipt.json', location + '/authenticated-source-stanza.txt', location + '/unpack-validation.json', 'apt-authentication.tar.gz', 'build/Collector.Dockerfile', 'build/source-policy.json'])
            # Built-Using sources may have no installed binary or installed notice.
            # Retain their original notices from the authenticated source archives.
            for material in component['source_files']:
                retain_archive_notices(output / material['path'], output, component)
        elif component['name'] == 'openmedia':
            revision = inventories[0]['source_revision']; target = output / 'materials' / ('openmedia-' + revision + '.tar.gz'); target.parent.mkdir(parents=True, exist_ok=True)
            run(['git', '-C', str(repository), 'archive', '--format=tar.gz', '--output', str(target.resolve()), revision, 'src', 'scripts', 'release', '.github', '.dockerignore', 'Dockerfile', 'pyproject.toml', 'uv.lock', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md'])
            inspect_archive(target)
            component['source_files'] = [{'path': str(target.relative_to(output)), 'url': 'https://github.com/hman-pro/openmedia/tree/' + revision, 'sha256': digest(target), 'size': target.stat().st_size, 'role': 'application-git-archive'}]
        else:
            for material in component['source_files']:
                name = material['url'].rsplit('/', 1)[-1]
                safe_path(name)
                material['path'] = 'materials/' + material['sha256'] + '/' + name
                target = acquire(material, output / material['path'])
                retain_archive_notices(target, output, component)
                if material.get('role') == 'notice': component.setdefault('notice_paths', []).append(material['path'])
        require(component.get('notice_paths'), 'Missing component notices: ' + component['name'])
        for notice in component['notice_paths']: require((output / notice).is_file(), 'Missing required notice file')
        component['coverage'] = 'complete'


def main():
    parser = argparse.ArgumentParser(description=__doc__); subs = parser.add_subparsers(dest='command', required=True)
    sub = subs.add_parser('inventory'); sub.add_argument('--image', required=True); sub.add_argument('--platform', required=True); sub.add_argument('--output', type=Path, required=True)
    sub = subs.add_parser('collect'); sub.add_argument('--inventory', action='append', required=True); sub.add_argument('--policy', required=True); sub.add_argument('--lock', required=True); sub.add_argument('--output', type=Path, required=True); sub.add_argument('--repository', default='.')
    args = parser.parse_args()
    try:
        if args.command == 'inventory': inventory(args.image, args.platform, args.output)
        else: collect(args.inventory, read_json(args.policy), tomllib.loads(Path(args.lock).read_text()), args.output, args.repository)
    except (ReleaseError, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        detail = str(error) if isinstance(error, ReleaseError) else getattr(error, 'stderr', None) or type(error).__name__
        safe = re.sub(r'[^A-Za-z0-9 .:/+_@()=-]', '?', str(detail))[:320]
        progress_path = args.output / 'collection-progress.json'
        if progress_path.exists():
            progress = read_json(progress_path); progress.update(result='fail', failure_category=safe, coverage='missing'); write_json(progress_path, progress)
        raise SystemExit('Source collection failed: ' + safe + '; inspect collection-progress.json') from None


if __name__ == '__main__': main()
