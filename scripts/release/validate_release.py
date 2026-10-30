#!/usr/bin/env python3
"""Release identities and redistribution gates. Python 3.11+, standard library only.

Parsing is intentionally separate from publication authority. Verification uses gh's
established Sigstore roots and authenticated certificate output, never roots from assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
from urllib.parse import urlparse, quote
import zipfile

REPOSITORY = 'hman-pro/openmedia'
REPOSITORY_ID = 1380348601
IMAGE = 'ghcr.io/' + REPOSITORY
SOURCE = 'https://github.com/' + REPOSITORY
WORKFLOW = '.github/workflows/release.yml'
PLATFORMS = {'linux/amd64', 'linux/arm64'}
SEMVER = re.compile(r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-((?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][A-Za-z0-9-]*)(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][A-Za-z0-9-]*))*))?\Z')
HEX = re.compile(r'[a-f0-9]{64}\Z')
COMMIT = re.compile(r'[a-f0-9]{40}\Z')
PRE_PUSH_GATES = ('authority', 'pins', 'controlled', 'amd64', 'arm64', 'coverage', 'sources_public', 'amd64_import', 'arm64_import')
NON_MATERIAL = {'release-manifest.json', 'release-manifest.sigstore.json', 'provenance.sigstore.json', 'SHA256SUMS'}


class ReleaseError(ValueError):
    """A bounded, nonsecret release validation failure."""


def require(condition, message):
    if not condition:
        raise ReleaseError(message)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def default_policy():
    return {'schema_version': 1, 'repository': REPOSITORY, 'repository_id': REPOSITORY_ID,
            'workflow': WORKFLOW, 'issuer': 'https://token.actions.githubusercontent.com',
            'runner_environment': 'github-hosted', 'gh_version': '2.103.3',
            'asset_origin': SOURCE + '/releases/download/'}


def validate_policy(policy):
    require(set(policy) == set(default_policy()), 'Unsupported trust policy fields')
    # The numeric ID is independently committed here; an asset cannot choose its anchor.
    for key, value in default_policy().items():
        require(policy.get(key) == value, 'Untrusted verification policy: ' + key)
    return policy


def sha(value):
    return isinstance(value, str) and bool(HEX.fullmatch(value))


def oci_digest(value):
    return isinstance(value, str) and value.startswith('sha256:') and sha(value[7:])


def safe_path(value):
    require(isinstance(value, str) and value and '\\' not in value and '\x00' not in value, 'Invalid material path')
    path = PurePosixPath(value)
    require(not path.is_absolute() and '..' not in path.parts and path.parts, 'Unsafe material path')
    return path


def material_path(root, name):
    safe_path(name)
    root = Path(root).resolve(); path = root / name
    require(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Unsafe material location')
    require(path.is_file(), 'Missing material: ' + name)
    return path


def archive_path(value):
    # systemd sources use literal POSIX filenames such as dev-mapper-foo\x2dbar.
    # Accept the spelled-out hex escape only; never decode it into a path character.
    require(isinstance(value, str), 'Invalid archive path')
    safe_path(re.sub(r'\\x[0-9a-fA-F]{2}', '_', value))
    return PurePosixPath(value)


def inspect_archive(path, max_expanded=32 * 1024**3):
    """Validate paths, link targets, types and expansion without executing/extracting."""
    total = 0; names = set(); directories = {}; links = {}; fifos = set(); member_names = []
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                archive_path(info.filename)
                require(info.filename not in names, 'Duplicate archive member')
                names.add(info.filename); total += info.file_size
                mode = (info.external_attr >> 16) & 0o170000
                require(mode in (0, 0o100000, 0o040000), 'Unsupported ZIP member type')
                require(total <= max_expanded, 'Oversized source archive')
        return
    with tarfile.open(path, 'r:*') as archive:
        for member in archive:
            if member.isdir() and member.name in ('.', './'): continue
            name = archive_path(member.name)
            normalized = str(name)
            if normalized in names and member.isdir():
                require(member.size == 0 and directories.get(normalized) == (member.mode, member.uid, member.gid), 'Conflicting duplicate archive directory')
                continue
            require(normalized not in names, 'Duplicate archive member')
            names.add(normalized); member_names.append(normalized)
            if member.isdir(): directories[normalized] = (member.mode, member.uid, member.gid)
            require(member.isfile() or member.isdir() or member.issym() or member.islnk() or member.isfifo(), 'Unsupported archive member type')
            if member.isfifo():
                # dpkg's original source includes FIFO test fixtures. Inspection
                # never opens/extracts them; dpkg-source unpacks only in the collector.
                require(member.size == 0, 'FIFO archive member has data')
                fifos.add(normalized)
            if member.issym() or member.islnk():
                target = member.linkname
                require(target and not target.startswith('/') and '\\' not in target and '\x00' not in target, 'Unsafe archive link')
                parts = list(name.parent.parts) if member.issym() else []
                for part in PurePosixPath(target).parts:
                    if part == '..':
                        require(bool(parts), 'Escaping archive link'); parts.pop()
                    elif part != '.': parts.append(part)
                require(bool(parts) or member.issym(), 'Invalid archive link')
                links[str(name)] = '/'.join(parts)
            total += member.size
            require(total <= max_expanded, 'Oversized source archive')
    # Resolve link chains in every member path, including directory symlinks.
    # Reject cycles and any member traversing a link: upstream source trees may use
    # links, but writing descendant members through them is unsafe to unpack.
    for member_name in member_names:
        parts = PurePosixPath(member_name).parts
        for count in range(1, len(parts)):
            require('/'.join(parts[:count]) not in links, 'Archive member traverses a link')
            require('/'.join(parts[:count]) not in fifos, 'Archive member traverses a FIFO')
    for original in links:
        current = links[original]; seen = {original}
        while True:
            parts = PurePosixPath(current).parts
            found = next(('/'.join(parts[:n]) for n in range(1, len(parts)+1) if '/'.join(parts[:n]) in links), None)
            if found is None: break
            require(found not in seen, 'Archive link cycle'); seen.add(found)
            tail = parts[len(PurePosixPath(found).parts):]
            current = '/'.join(PurePosixPath(links[found]).parts + tail)
            if current: safe_path(current)
    # Inspection does not execute or extract upstream code.


def validate_artifact(item, version):
    name = item.get('name'); safe_path(name)
    require('/' not in name and name not in NON_MATERIAL, 'Cyclic or nested manifest material')
    require(sha(item.get('sha256')), 'Missing material SHA256')
    require(type(item.get('size')) is int and item['size'] > 0, 'Invalid material size')
    require(isinstance(item.get('media_type'), str) and '/' in item['media_type'], 'Missing media type')
    allowed = [SOURCE + '/releases/download/' + tag + '/' + quote(name, safe='') for tag in (version, 'sources-' + version)]
    require(item.get('url') in allowed, 'Unsupported public material origin')


def validate_platform(record, revision=None, version=None, promoted=True):
    require(record.get('platform') in PLATFORMS, 'Unsupported platform')
    arch = record['platform'].split('/')[1]
    runner = record.get('runner', {})
    require(runner.get('label') == ('ubuntu-24.04' if arch == 'amd64' else 'ubuntu-24.04-arm'), 'Platform was not built on the required native runner')
    require(runner.get('architecture') == arch and bool(runner.get('image_revision')), 'Missing native runner identity')
    for key in ('image_config_id',): require(oci_digest(record.get(key)), 'Invalid ' + key)
    require(sha(record.get('archive_hash')), 'Invalid archive hash')
    require(record['image_config_id'] != 'sha256:' + record['archive_hash'], 'Archive hash is not config identity')
    require(record.get('smoke_result') == {'result': 'pass', 'image_config_id': record['image_config_id']}, 'Smoke/config identity mismatch')
    require(record.get('base_digests') and all(oci_digest(v) for v in record['base_digests'].values()), 'Missing effective base digests')
    require(record.get('tool_versions') and all(record['tool_versions'].values()), 'Missing tool versions')
    if promoted: require(oci_digest(record.get('platform_digest')), 'Missing platform digest')
    sbom = record.get('sbom', {}); inventory = record.get('component_inventory', {})
    require(sbom.get('name') == 'sbom-' + arch + '.spdx.json' and sha(sbom.get('sha256')), 'Invalid architecture SBOM')
    require(inventory.get('name') == 'inventory-' + arch + '.json' and sha(inventory.get('sha256')), 'Missing component inventory')
    require(inventory.get('platform') == record['platform'], 'Wrong inventory platform')
    if revision: require(inventory.get('source_revision') == revision, 'Stale inventory source revision')
    if version: require(record.get('version') == version and inventory.get('version') == version, 'Stale platform version')
    return record


def validate_manifest(item, version=None, revision=None, index_digest=None):
    require(item.get('schema_version') == 1, 'Unsupported release schema')
    tag = item.get('version'); require(isinstance(tag, str) and SEMVER.fullmatch(tag), 'Invalid release tag')
    require(isinstance(item.get('package_version'), str) and re.fullmatch(r'[0-9]+(?:\.[0-9]+)+(?:[A-Za-z0-9.]+)?', item['package_version']), 'Missing installed package version')
    require(COMMIT.fullmatch(str(item.get('source_revision', ''))), 'Invalid full source revision')
    require(item.get('source_repository') == SOURCE and item.get('repository_id') == REPOSITORY_ID, 'Wrong source repository identity')
    require(item.get('workflow') == WORKFLOW, 'Wrong workflow')
    run = item.get('workflow_run', {})
    require(type(run.get('id')) is int and run['id'] > 0 and type(run.get('attempt')) is int and run['attempt'] > 0, 'Missing workflow run identity')
    require(item.get('source_release_tag') == 'sources-' + tag, 'Source release tag mismatch')
    require(item.get('source_release_url') == SOURCE + '/releases/tag/sources-' + tag, 'Source release URL mismatch')
    require(oci_digest(item.get('index_digest')), 'Invalid OCI index digest')
    for expected, actual in [(version, tag), (revision, item['source_revision']), (index_digest, item['index_digest'])]:
        if expected is not None: require(expected == actual, 'Expected published identity mismatch')
    require(type(item.get('preview')) is bool, 'Missing preview status')
    gates = item.get('gates'); require(isinstance(gates, list) and bool(gates), 'Missing acceptance gate references')
    for gate in gates:
        require(gate.get('gate_scope') in ('feature-008', 'inherited-stable-readiness') and gate.get('result') in ('pending', 'pass', 'fail', 'blocked') and bool(gate.get('gate_id')), 'Invalid gate record')
    if any(g['result'] != 'pass' for g in gates): require(item['preview'] and '-' in tag, 'Open gates require a preview tag/status')
    records = item.get('platforms', [])
    require(len(records) == 2 and {p.get('platform') for p in records} == PLATFORMS, 'Exactly both native architectures required')
    assets = item.get('artifacts'); require(isinstance(assets, list) and bool(assets), 'Missing artifacts')
    for asset in assets: validate_artifact(asset, tag)
    by_name = {a['name']: a for a in assets}
    require(len(by_name) == len(assets), 'Duplicate artifacts')
    require({'release-index.json', 'source-manifest.json', 'sbom-amd64.spdx.json', 'sbom-arm64.spdx.json'} <= by_name.keys(), 'Missing required public evidence')
    require(by_name['release-index.json']['sha256'] == item['index_digest'][7:], 'Index byte hash mismatch')
    for platform in records:
        validate_platform(platform, item['source_revision'], tag)
        for field in ('sbom', 'component_inventory'):
            reference = platform[field]
            require(reference['name'] in by_name and by_name[reference['name']]['sha256'] == reference['sha256'], 'Swapped/stale platform material')
    return item



def assemble_release(version, source_revision, package_version, platforms, artifacts, index_digest, workflow_run, gates):
    """Assemble a final record from checked identities, including existing versions.

    No registry availability query or future signature is part of this pure boundary.
    """
    value = {'schema_version': 1, 'version': version, 'package_version': package_version,
             'source_revision': source_revision, 'source_repository': SOURCE,
             'repository_id': REPOSITORY_ID, 'workflow': WORKFLOW, 'workflow_run': workflow_run,
             'source_release_tag': 'sources-' + version,
             'source_release_url': SOURCE + '/releases/tag/sources-' + version,
             'index_digest': index_digest, 'platforms': platforms, 'artifacts': artifacts,
             'preview': '-' in version, 'gates': gates}
    return validate_manifest(value, version, source_revision, index_digest)

def validate_source_manifest(source):
    require(source.get('schema_version') == 1 and bool(source.get('components')) and bool(source.get('inventories')), 'Missing actual-image source coverage')
    components = {c.get('component_id'): c for c in source['components']}
    require(len(components) == len(source['components']), 'Duplicate source components')
    for component in components.values():
        require(component.get('kind') in ('debian', 'application-python', 'system-python', 'unmanaged', 'embedded'), 'Unknown source component kind')
        for key in ('name', 'version', 'architectures', 'license', 'notice_paths', 'source_identity', 'source_files', 'build_materials'):
            require(bool(component.get(key)), 'Missing component ' + key)
        require(component.get('coverage') == 'complete', 'Incomplete component coverage')
        require(set(component['architectures']) <= PLATFORMS, 'Unknown source architecture')
        for material in component['source_files']:
            safe_path(material.get('path')); require(sha(material.get('sha256')) and material.get('size', 0) > 0 and material.get('url'), 'Unverified source acquisition')
        require(isinstance(component.get('incorporated_sources'), list), 'Missing incorporated-source review')
    for inventory in source['inventories']:
        require(bool(inventory.get('components')), 'Empty image inventory')
        for actual in inventory['components']:
            key = actual.get('component_id'); require(key in components, 'Uncovered actual-image component')
            reviewed = components[key]
            require(actual.get('version') == reviewed['version'] and inventory['platform'] in reviewed['architectures'], 'Source/inventory version or architecture mismatch')
            require(actual.get('source_identity') == reviewed['source_identity'], 'Source identity mismatch')
            for edge in actual.get('incorporated_sources', []):
                require(any(c['source_identity'] == edge for c in components.values()), 'Missing Built-Using/incorporated source')
    return source


def validate_sources(directory):
    root = Path(directory); source = validate_source_manifest(read_json(root / 'source-manifest.json'))
    if not (root / 'materials').is_dir():
        validate_public_sources(root, source, {p['name']: p for p in source.get('parts', [])})
        return source
    for component in source['components']:
        for item in component['source_files']:
            path = material_path(root, item['path'])
            require(digest(path) == item['sha256'] and path.stat().st_size == item['size'], 'Source material checksum mismatch')
            if tarfile.is_tarfile(path) or zipfile.is_zipfile(path): inspect_archive(path)
        for name in component['notice_paths'] + component['build_materials']:
            material_path(root, name)
    for part in source.get('parts', []):
        path = material_path(root, part['name'])
        require(digest(path) == part['sha256'] and path.stat().st_size == part['size'], 'Source part mismatch')
        inspect_archive(path)
    validate_public_sources(root, source, {p['name']: p for p in source.get('parts', [])})
    return source


def validate_bundle(directory):
    root = Path(directory); manifest = validate_manifest(read_json(root / 'release-manifest.json'))
    for asset in manifest['artifacts']:
        path = material_path(root, asset['name'])
        require(digest(path) == asset['sha256'] and path.stat().st_size == asset['size'], 'Material checksum mismatch: ' + asset['name'])
        if tarfile.is_tarfile(path) or zipfile.is_zipfile(path): inspect_archive(path)
    index = read_json(root / 'release-index.json')
    require(index.get('schemaVersion') == 2 and index.get('mediaType') == 'application/vnd.oci.image.index.v1+json', 'Not an OCI image index')
    children = index.get('manifests', [])
    require(len(children) == 2, 'Unexpected index descriptors')
    actual = {d['platform']['os'] + '/' + d['platform']['architecture']: d['digest'] for d in children}
    require(actual == {p['platform']: p['platform_digest'] for p in manifest['platforms']}, 'OCI index child/platform mismatch')
    source = validate_source_manifest(read_json(root / 'source-manifest.json'))
    validate_public_sources(root, source, {a['name']: a for a in manifest['artifacts']})
    inventories = {x['platform']: x for x in source['inventories']}
    require(set(inventories) == PLATFORMS, 'Incomplete source architecture coverage')
    for platform in manifest['platforms']:
        child_name = 'manifest-' + platform['platform'].split('/')[1] + '.json'
        require(child_name in {a['name'] for a in manifest['artifacts']}, 'Missing raw child manifest')
        child_path = material_path(root, child_name)
        require('sha256:' + digest(child_path) == platform['platform_digest'], 'Raw child manifest digest mismatch')
        child = read_json(child_path)
        require(child.get('config', {}).get('digest') == platform['image_config_id'], 'Child/config identity mismatch')
        inventory = read_json(root / platform['component_inventory']['name'])
        require(inventory == inventories[platform['platform']], 'Stale actual-image inventory')
        require(inventory.get('image_config_id') == platform['image_config_id'] and inventory.get('version') == manifest['version'] and inventory.get('source_revision') == manifest['source_revision'], 'Image/source identity join failed')
        sbom = read_json(root / platform['sbom']['name'])
        require(sbom.get('spdxVersion', '').startswith('SPDX-') and bool(sbom.get('packages')), 'Empty/invalid SPDX inventory')
    return manifest



def validate_public_sources(root, source, artifacts):
    """Join every source, installed notice and build file inside downloaded parts."""
    expected = {}
    for component in source['components']:
        for material in component['source_files']:
            expected[material['path']] = {'sha256': material['sha256'], 'size': material['size']}
    auxiliary = source.get('auxiliary_files', {})
    for component in source['components']:
        for name in component['notice_paths'] + component['build_materials']:
            require(name in auxiliary, 'Unhashed notice/build material')
            expected[name] = auxiliary[name]
    require(bool(source.get('parts')), 'Missing logical source/notice archives')
    observed = set()
    for part in source['parts']:
        require(part['name'] in artifacts and artifacts[part['name']]['sha256'] == part['sha256'], 'Unbound source part')
        path = material_path(root, part['name'])
        require(digest(path) == part['sha256'] and path.stat().st_size == part['size'], 'Source part checksum mismatch')
        inspect_archive(path)
        with tarfile.open(path, 'r:*') as archive:
            for member in archive:
                require(member.isfile(), 'Logical source parts contain only regular material files')
                require(member.name in expected and member.name not in observed, 'Unexpected/duplicate source material')
                observed.add(member.name); item = expected[member.name]
                require(member.size == item['size'], 'Packed source size mismatch')
                with tempfile.TemporaryDirectory(prefix='openmedia-material-') as temporary:
                    target = Path(temporary) / 'material'
                    with target.open('wb') as output:
                        import shutil
                        shutil.copyfileobj(archive.extractfile(member), output)
                    require(digest(target) == item['sha256'], 'Packed source hash mismatch')
                    if tarfile.is_tarfile(target) or zipfile.is_zipfile(target): inspect_archive(target)
    require(observed == set(expected), 'Missing packed sources/notices/build materials')


def emit_checksums(directory):
    root = Path(directory)
    names = sorted(p.name for p in root.iterdir() if p.is_file() and p.name != 'SHA256SUMS')
    (root / 'SHA256SUMS').write_text(''.join(digest(root / name) + '  ' + name + '\n' for name in names))


def anonymous_environment(original, directory):
    root = Path(directory)
    result = {k: v for k, v in original.items() if k in ('PATH', 'SYSTEMROOT', 'TMPDIR', 'SSL_CERT_FILE', 'SSL_CERT_DIR', 'HOME')}
    result.update(GH_CONFIG_DIR=str(root / 'gh'), DOCKER_CONFIG=str(root / 'docker'), GH_PROMPT_DISABLED='1')
    return result


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs).stdout


def check_verified_attestations(results, policy, version, revision, subject, subject_name=None):
    require(isinstance(results, list) and bool(results), 'No verified attestations')
    identity = SOURCE + '/' + policy['workflow'] + '@refs/tags/' + version
    for result in results:
        verified = result.get('verificationResult', {})
        cert = verified.get('signature', {}).get('certificate', {})
        require(str(cert.get('sourceRepositoryIdentifier')) == str(policy['repository_id']), 'Wrong signed numeric repository ID')
        require(cert.get('sourceRepositoryURI') == SOURCE, 'Wrong signed repository URI')
        require(cert.get('sourceRepositoryDigest') == revision and cert.get('sourceRepositoryRef') == 'refs/tags/' + version, 'Wrong signed source revision/ref')
        require(cert.get('subjectAlternativeName') == identity and cert.get('issuer') == policy['issuer'], 'Wrong signing workflow/issuer')
        require(cert.get('runnerEnvironment') == policy['runner_environment'], 'Untrusted builder environment')
        statement = verified.get('statement', {})
        require(any(x.get('digest', {}).get('sha256') == subject and (subject_name is None or x.get('name') == subject_name) for x in statement.get('subject', [])), 'Wrong authenticated artifact subject')
    return results


def verify(directory, image, version, revision, policy):
    validate_policy(policy)
    require(image.startswith(IMAGE + '@sha256:') and oci_digest(image[len(IMAGE)+1:]), 'Invalid immutable image reference')
    manifest = validate_bundle(directory)
    validate_manifest(manifest, version, revision, image.split('@')[1])
    root = Path(directory).resolve()
    with tempfile.TemporaryDirectory(prefix='openmedia-verify-') as temporary:
        environment = anonymous_environment(os.environ, temporary)
        output = run(['gh', '--version'], env=environment)
        require(output.startswith('gh version ' + policy['gh_version'] + ' '), 'Incorrect GitHub CLI version')
        for name, bundle in [('release-index.json', 'provenance.sigstore.json'), ('release-manifest.json', 'release-manifest.sigstore.json')]:
            command = ['gh', 'attestation', 'verify', str(root / name), '--bundle', str(root / bundle), '--repo', policy['repository'],
                       '--signer-workflow', 'github.com/' + policy['repository'] + '/' + policy['workflow'], '--source-digest', revision,
                       '--source-ref', 'refs/tags/' + version, '--cert-identity', SOURCE + '/' + policy['workflow'] + '@refs/tags/' + version,
                       '--cert-oidc-issuer', policy['issuer'], '--deny-self-hosted-runners', '--format', 'json']
            check_verified_attestations(json.loads(run(command, env=environment)), policy, version, revision, digest(root / name), IMAGE if name == 'release-index.json' else 'release-manifest.json')
    return manifest


def authorize_publication(context):
    require(context.get('repository') == REPOSITORY and context.get('repository_id') == REPOSITORY_ID, 'Wrong publishing repository')
    require(context.get('event') == 'push' and context.get('ref_type') == 'tag', 'Publication requires maintainer tag push')
    require(SEMVER.fullmatch(str(context.get('version', ''))) and '-' in context['version'], 'Only preview publication is currently enabled')
    require(COMMIT.fullmatch(str(context.get('revision', ''))) and context.get('source_revision') == context['revision'], 'Missing matching source tag')
    require(context.get('actor_permission') in ('admin', 'maintain', 'write') and context.get('tag_rules_verified') is True, 'Maintainer tag authority not established')
    require(context.get('immutable_releases') is True, 'Immutable releases must be enabled')
    require(context.get('version_exists') is False, 'Exact image version already exists or availability is unknown')
    return context


def require_pre_push(gates, action=None):
    require(set(gates) == set(PRE_PUSH_GATES) and all(gates[x] is True for x in PRE_PUSH_GATES), 'Incomplete pre-push gate set')
    if action: return action()


def failure_state(stage):
    require(stage in ('images_published', 'evidence_verified', 'release_finalized'), 'Unknown post-push stage')
    return {'state': 'finalized_incomplete' if stage == 'release_finalized' else 'draft_incomplete', 'retain_sources': True, 'replace_assets': False, 'accepted': False}


def archive_config(path):
    """Read the real OCI config bytes from Docker save; do not trust inspect .Id."""
    with tarfile.open(path, 'r:*') as archive:
        manifest = json.load(archive.extractfile('manifest.json'))
        require(len(manifest) == 1, 'Archive must contain exactly one image')
        name = manifest[0]['Config']; safe_path(name)
        content = archive.extractfile(name).read()
        value = json.loads(content)
        return 'sha256:' + hashlib.sha256(content).hexdigest(), value


def image_config(image):
    with tempfile.TemporaryDirectory(prefix='openmedia-config-') as temporary:
        path = Path(temporary) / 'image.tar'
        run(['docker', 'image', 'save', '--output', str(path), image])
        return archive_config(path)


def promotion(record, image):
    validate_platform(record, promoted=False)
    archive = Path(record['archive_path'])
    require(digest(archive) == record['archive_hash'], 'Transferred archive checksum mismatch')
    expected, _ = archive_config(archive)
    require(expected == record['image_config_id'], 'Archive config identity mismatch')
    imported, config = image_config(image)
    require(imported == expected, 'Imported image config identity mismatch')
    require(config.get('os') + '/' + config.get('architecture') == record['platform'], 'Imported platform mismatch')
    labels = config.get('config', {}).get('Labels', {})
    require(labels.get('org.opencontainers.image.version') == record['version'] and labels.get('org.opencontainers.image.revision') == record['component_inventory']['source_revision'], 'Imported release labels mismatch')
    return imported


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    for command in ('sources', 'bundle', 'verify', 'assemble'):
        sub = subs.add_parser(command); sub.add_argument('--directory', type=Path, required=True)
        if command == 'verify':
            for key in ('image', 'version', 'source-revision', 'policy'): sub.add_argument('--' + key, required=True)
    sub = subs.add_parser('promotion'); sub.add_argument('--record', required=True); sub.add_argument('--image', required=True)
    sub = subs.add_parser('authorize'); sub.add_argument('--context', required=True)
    sub = subs.add_parser('config'); sub.add_argument('--image', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'sources': validate_sources(args.directory)
        elif args.command == 'bundle': validate_bundle(args.directory); emit_checksums(args.directory)
        elif args.command == 'assemble':
            validate_manifest(read_json(args.directory / 'release-manifest.json')); validate_bundle(args.directory); emit_checksums(args.directory)
        elif args.command == 'verify': verify(args.directory, args.image, args.version, args.source_revision, read_json(args.policy))
        elif args.command == 'promotion': promotion(read_json(args.record), args.image)
        elif args.command == 'authorize': authorize_publication(read_json(args.context))
        elif args.command == 'config': print(image_config(args.image)[0]); return
        print('Release check passed: ' + args.command)
    except (ReleaseError, OSError, ValueError, KeyError, TypeError, tarfile.TarError, subprocess.SubprocessError):
        print('Release check failed: ' + args.command + '; inspect sanitized validation records', file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == '__main__': main()
