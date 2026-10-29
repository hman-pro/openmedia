#!/usr/bin/env python3
"""Stage-specific release command boundaries, shared by workflows and controlled tests.

No application build command exists here. Once any image is pushed, failures retain
source releases and immutable images and keep distribution explicitly incomplete.
"""
from __future__ import annotations
import argparse
import copy
import fnmatch
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import quote
from urllib.request import urlopen, Request

from validate_release import (REPOSITORY, REPOSITORY_ID, SOURCE, IMAGE, WORKFLOW, PLATFORMS,
    SEMVER, ReleaseError, require, read_json, write_json, digest, run, archive_config,
    validate_platform, validate_sources, validate_manifest, validate_bundle, promotion,
    authorize_publication, require_pre_push, default_policy, verify, anonymous_environment,
    emit_checksums, assemble_release)


def raw_manifest(reference, platform=None):
    command = ['regctl', 'manifest', 'get', reference, '--format', 'raw-body']
    if platform: command += ['--platform', platform]
    return subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def api(path): return json.loads(run(['gh', 'api', '-H', 'X-GitHub-Api-Version: 2026-03-10', path]))


def release_identity():
    version = os.environ['GITHUB_REF_NAME']; revision = os.environ['GITHUB_SHA']
    require(os.environ.get('GITHUB_EVENT_NAME') == 'push' and os.environ.get('GITHUB_REF_TYPE') == 'tag', 'Publication requires a version tag push')
    require(SEMVER.fullmatch(version) and '-' in version, 'Only exact preview version tags are currently publishable')
    require(os.environ.get('GITHUB_REPOSITORY') == REPOSITORY and os.environ.get('GITHUB_REPOSITORY_ID') == str(REPOSITORY_ID), 'Wrong workflow repository')
    return version, revision


def audit_pins(root=Path('.')):
    from install_tools import PINS
    reviewed_actions = {'actions/checkout': '3d3c42e5aac5ba805825da76410c181273ba90b1', 'actions/setup-python': '6d4fd22b20465ccc0f7354476588e8df7c9ca0e0', 'actions/upload-artifact': 'cf430e030ddbb5b0abf93d22962f4752f3646cd9', 'actions/download-artifact': '9000827ccba6bdab643e8b6fd33ac0654aef8333', 'actions/attest': '1e69f48acb82d1966a394da916b4c1698aa569d6', 'docker/setup-buildx-action': 'f87e5991a6d7451dcb8d9637bfbc97413f497069', 'docker/login-action': '81c6f93d4bc991e510b342a00b419b3bb4efc5c6'}
    require(all(len(pin) == 64 for tool in PINS.values() for pin in tool[3].values()), 'Unpinned release tool')
    for path in (root / '.github/workflows').glob('*.yml'):
        text = path.read_text()
        require('pull_request_target' not in text and 'write-all' not in text, 'Unsafe workflow trigger/permissions')
        for action in re.findall(r'^\s*-?\s*uses:\s*(\S+)', text, re.M):
            if not action.startswith('./'):
                name, separator, pin = action.partition('@')
                require(separator and reviewed_actions.get(name) == pin, 'Unreviewed external action pin')
            require(action.startswith('./') or re.fullmatch(r'[A-Za-z0-9_./-]+@[a-f0-9]{40}', action), 'Mutable workflow action')
    dockerfile = (root / 'Dockerfile').read_text()
    require(len(re.findall(r'^ARG (?:PYTHON|UV|DENO)_IMAGE=\S+@sha256:[a-f0-9]{64}$', dockerfile, re.M)) == 3, 'Mutable runtime input')
    ci = (root / '.github/workflows/ci.yml').read_text()
    require(re.search(r'^permissions:\n  contents: read$', ci, re.M) and not re.search(r'^\s+(?:contents|packages|id-token|attestations|actions|checks|deployments|issues|pull-requests|statuses):\s*write\s*$', ci, re.M), 'CI must remain read-only')
    return True


def peel_tag(tag):
    obj = api('repos/' + REPOSITORY + '/git/ref/tags/' + quote(tag, safe=''))['object']
    while obj['type'] == 'tag': obj = api('repos/' + REPOSITORY + '/git/tags/' + obj['sha'])['object']
    require(obj['type'] == 'commit', 'Release tag is not a commit'); return obj['sha']


def check_tag_rules(version, rulesets):
    for ref in ('refs/tags/' + version, 'refs/tags/sources-' + version):
        applicable = []
        for ruleset in rulesets:
            if ruleset.get('target') != 'tag' or ruleset.get('enforcement') != 'active': continue
            condition = ruleset.get('conditions', {}).get('ref_name', {})
            include = condition.get('include', []); exclude = condition.get('exclude', [])
            if any(pattern == '~ALL' or fnmatch.fnmatchcase(ref, pattern) for pattern in include) and not any(fnmatch.fnmatchcase(ref, p) for p in exclude): applicable.append(ruleset)
        require(applicable, 'No active tag authority ruleset')
        types = {rule['type'] for ruleset in applicable for rule in ruleset.get('rules', [])}
        require({'creation', 'update', 'deletion'} <= types, 'Tag creation/mutation/deletion are not all restricted')
        for ruleset in applicable:
            for bypass in ruleset.get('bypass_actors', []):
                require(bypass.get('actor_type') == 'RepositoryRole' and bypass.get('actor_id') in (4, 5) and bypass.get('bypass_mode') == 'always', 'Tag bypass must be restricted to maintainers/admins')
    return True


def unused_version(version):
    try:
        run(['regctl', 'manifest', 'head', IMAGE + ':' + version])
    except subprocess.CalledProcessError as error:
        message = (error.stderr or '').lower()
        require('manifest unknown' in message or ('404' in message and 'not found' in message), 'Image version availability could not be established')
        return True
    raise ReleaseError('Exact image version already exists')


def authority(directory):
    version, revision = release_identity(); directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    repository = api('repos/' + REPOSITORY)
    require(repository['id'] == REPOSITORY_ID and repository['visibility'] == 'public', 'Wrong or nonpublic canonical repository')
    require(peel_tag(version) == revision and peel_tag('sources-' + version) == revision, 'Missing matching source/version tag pair')
    permission = api('repos/' + REPOSITORY + '/collaborators/' + quote(os.environ['GITHUB_ACTOR'], safe='') + '/permission')['permission']
    require(permission in ('admin', 'maintain', 'write'), 'Tag actor is not a maintainer')
    rulesets = [api('repos/' + REPOSITORY + '/rulesets/' + str(x['id'])) for x in api('repos/' + REPOSITORY + '/rulesets?includes_parents=true')]
    check_tag_rules(version, rulesets); audit_pins(); unused_version(version)
    # Immutability is verified from the completed sources-only release before any
    # image push. Its public immutable flag avoids granting Actions admin permission.
    context = {'repository': REPOSITORY, 'repository_id': REPOSITORY_ID, 'version': version,
               'revision': revision, 'source_revision': revision, 'event': os.environ['GITHUB_EVENT_NAME'],
               'ref_type': os.environ['GITHUB_REF_TYPE'], 'actor_permission': permission,
               'tag_rules_verified': True, 'version_exists': False, 'rulesets': rulesets}
    write_json(directory / 'authority.json', context)


def download_public(url, destination, expected):
    destination = Path(destination)
    with urlopen(Request(url, headers={'User-Agent': 'OpenMedia-release-verifier'}), timeout=120) as response, destination.open('wb') as output:
        require(response.url.startswith('https://'), 'Non-HTTPS public asset redirect')
        remaining = expected['size'] + 1
        while remaining:
            block = response.read(min(1024*1024, remaining))
            if not block: break
            output.write(block); remaining -= len(block)
    require(destination.stat().st_size == expected['size'] and digest(destination) == expected['sha256'], 'Anonymous material download checksum failed')


def public_source_assets(directory, version):
    directory = Path(directory); source = read_json(directory / 'source-manifest.json')
    names = ['source-manifest.json'] + [p['name'] for p in source['parts']] + ['inventory-amd64.json', 'inventory-arm64.json']
    return [{'name': name, 'sha256': digest(directory / name), 'size': (directory / name).stat().st_size,
             'media_type': 'application/gzip' if name.endswith('.gz') else 'application/json',
             'url': SOURCE + '/releases/download/sources-' + version + '/' + quote(name, safe='')} for name in names]


def get_release(tag):
    try: return api('repos/' + REPOSITORY + '/releases/tags/' + quote(tag, safe=''))
    except subprocess.CalledProcessError as error:
        require('404' in (error.stderr or ''), 'Could not establish release state')
        return None


def create_draft(tag, revision, directory, title):
    existing = get_release(tag)
    if existing:
        require(existing['draft'] is True and not existing.get('assets'), 'Existing image release cannot be replaced')
        return existing
    notes = Path(directory) / 'release-notes.txt'
    notes.write_text('Preview; public distribution is INCOMPLETE until this workflow succeeds.\n\nInherited source/live gates and deployment acceptance remain open. Matching sources are retained even if later checks fail. Publication never deploys to a server.\n')
    run(['gh', 'release', 'create', tag, '--repo', REPOSITORY, '--verify-tag', '--target', revision, '--draft', '--prerelease', '--title', title, '--notes-file', str(notes)])
    return get_release(tag)


def stage_sources(directory):
    version, revision = release_identity(); directory = Path(directory)
    source = validate_sources(directory)
    require(all(i['version'] == version and i['source_revision'] == revision for i in source['inventories']), 'Stale sources for release tag')
    assets = public_source_assets(directory, version); tag = 'sources-' + version
    existing = get_release(tag)
    if existing and not existing['draft']:
        require(existing.get('immutable') is True, 'Existing source release is mutable')
        require({a['name'] for a in existing['assets']} == {a['name'] for a in assets}, 'Immutable source release has different assets')
    else:
        if existing: require(not existing['assets'], 'Existing populated source draft requires a new version')
        else: create_draft(tag, revision, directory, 'Matching sources for ' + version)
        run(['gh', 'release', 'upload', tag, '--repo', REPOSITORY] + [str(directory / a['name']) for a in assets])
        run(['gh', 'release', 'edit', tag, '--repo', REPOSITORY, '--draft=false'])
    published = get_release(tag)
    require(published and not published['draft'] and published.get('immutable') is True and peel_tag(tag) == revision, 'Completed immutable source release required')
    with tempfile.TemporaryDirectory(prefix='openmedia-public-source-') as temporary:
        for asset in assets: download_public(asset['url'], Path(temporary) / asset['name'], asset)
    write_json(directory / 'public-sources.json', {'version': version, 'source_revision': revision, 'immutable': True, 'assets': assets, 'source_manifest_hash': digest(directory / 'source-manifest.json')})
    create_draft(version, revision, directory, version + ' — incomplete preview')


def _same_run(receipt, revision):
    require(receipt.get('result') == 'pass' and receipt.get('source_revision') == revision and str(receipt.get('run_id')) == os.environ['GITHUB_RUN_ID'] and str(receipt.get('run_attempt')) == os.environ['GITHUB_RUN_ATTEMPT'], 'Controlled suite is not from this source/run/attempt')


def import_checked_archives(directory, records):
    """Validate and import BOTH checked artifacts before returning any push targets."""
    directory = Path(directory); imported = []
    for record in records:
        arch = record['platform'].split('/')[1]; archive = directory / ('native-' + arch) / ('image-' + arch + '.tar')
        record['archive_path'] = str(archive.resolve()); validate_platform(record, promoted=False)
        require(digest(archive) == record['archive_hash'] and archive_config(archive)[0] == record['image_config_id'], 'Transferred native archive mismatch')
    for record in records:
        arch = record['platform'].split('/')[1]
        run(['docker', 'image', 'load', '--input', record['archive_path']])
        local = 'openmedia:tested-' + arch
        promotion(record, local)
        imported.append((record, local))
    return imported


def promote(directory):
    version, revision = release_identity(); directory = Path(directory)
    audit_pins(); _same_run(read_json(directory / 'controlled/controlled.json'), revision)
    source_receipt = read_json(directory / 'public-source-receipt/public-sources.json')
    require(source_receipt['version'] == version and source_receipt['source_revision'] == revision and source_receipt['immutable'] is True, 'Wrong public source receipt')
    context = read_json(directory / 'authority/authority.json')
    context['immutable_releases'] = True; authorize_publication(context)
    require(context['version'] == version and context['revision'] == revision, 'Stale publication authority')
    source_dir = directory / 'matching-sources'; source = validate_sources(source_dir)
    require(digest(source_dir / 'source-manifest.json') == source_receipt['source_manifest_hash'], 'Stale source closure')
    require({i['platform'] for i in source['inventories']} == PLATFORMS, 'Missing actual architecture inventory')
    records = [read_json(directory / ('native-' + arch) / ('platform-' + arch + '.json')) for arch in ('amd64', 'arm64')]
    for record in records:
        validate_platform(record, revision, version, promoted=False)
        inventory_path = source_dir / record['component_inventory']['name']
        inventory = read_json(inventory_path)
        require(digest(inventory_path) == record['component_inventory']['sha256'] and inventory in source['inventories'], 'Pre-push source/native inventory hash mismatch')
        require(inventory['image_config_id'] == record['image_config_id'] and inventory['version'] == version and inventory['source_revision'] == revision, 'Pre-push image/source inventory join failed')
        sbom_path = directory / ('native-' + record['platform'].split('/')[1]) / record['sbom']['name']
        require(digest(sbom_path) == record['sbom']['sha256'] and read_json(sbom_path).get('spdxVersion', '').startswith('SPDX-') and bool(read_json(sbom_path).get('packages')), 'Pre-push SPDX inventory mismatch')
    imported = import_checked_archives(directory, records)
    with tempfile.TemporaryDirectory(prefix='openmedia-prepush-sources-') as temporary:
        for asset in source_receipt['assets']: download_public(asset['url'], Path(temporary) / asset['name'], asset)
    unused_version(version)
    require_pre_push(dict.fromkeys(('authority','pins','controlled','amd64','arm64','coverage','sources_public','amd64_import','arm64_import'), True))
    final = directory / 'final'; final.mkdir(exist_ok=True)
    for asset in source_receipt['assets']: shutil.copyfile(source_dir / asset['name'], final / asset['name'])
    # This is the first image write boundary. No earlier helper writes an image.
    write_json(directory / 'publication-stage.json', {'stage': 'images_published', 'version': version})
    child_media_types = []
    for record, local in imported:
        arch = record['platform'].split('/')[1]
        auxiliary = IMAGE + ':run-' + os.environ['GITHUB_RUN_ID'] + '-' + os.environ['GITHUB_RUN_ATTEMPT'] + '-' + arch
        run(['docker', 'image', 'tag', local, auxiliary]); run(['docker', 'image', 'push', auxiliary])
        raw = raw_manifest(auxiliary, record['platform'])
        child = final / ('manifest-' + arch + '.json'); child.write_bytes(raw)
        manifest = json.loads(raw)
        child_media_types.append(manifest.get('mediaType', ''))
        require(manifest['config']['digest'] == record['image_config_id'], 'Published child/config mismatch')
        record['platform_digest'] = 'sha256:' + digest(child)
        shutil.copyfile(directory / ('native-' + arch) / record['sbom']['name'], final / record['sbom']['name'])
    children = [IMAGE + '@' + r['platform_digest'] for r in records]
    if all(media.startswith('application/vnd.docker.') for media in child_media_types):
        # Buildx intentionally emits a Docker list when every child is Docker media.
        # Select OCI before the first exact-version write; never rewrite a version.
        run(['regctl', 'index', 'create', IMAGE + ':' + version, '--media-type', 'application/vnd.oci.image.index.v1+json'] + [argument for child in children for argument in ('--ref', child)])
    else:
        run(['docker', 'buildx', 'imagetools', 'create', '--tag', IMAGE + ':' + version] + children)
    raw = raw_manifest(IMAGE + ':' + version)
    (final / 'release-index.json').write_bytes(raw)
    index_digest = 'sha256:' + digest(final / 'release-index.json')
    require(run(['regctl', 'manifest', 'head', IMAGE + ':' + version, '--format', '{{.Digest}}']).strip() == index_digest, 'Registry/raw index digest mismatch')
    artifacts = list(source_receipt['assets'])
    for name in ['release-index.json', 'sbom-amd64.spdx.json', 'sbom-arm64.spdx.json', 'manifest-amd64.json', 'manifest-arm64.json']:
        path = final / name
        artifacts.append({'name': name, 'sha256': digest(path), 'size': path.stat().st_size, 'media_type': 'application/json', 'url': SOURCE + '/releases/download/' + version + '/' + name})
    package_versions = {c['version'] for i in source['inventories'] for c in i['components'] if c['name'] == 'openmedia'}
    require(len(package_versions) == 1, 'Installed package version mismatch')
    gates = [{'gate_id': 'F008-PUBLIC', 'gate_scope': 'feature-008', 'result': 'pending'}, {'gate_id': 'F008-SERVER', 'gate_scope': 'feature-008', 'result': 'pending'}, {'gate_id': 'I001-SOURCE-MATRIX', 'gate_scope': 'inherited-stable-readiness', 'result': 'pending'}]
    value = assemble_release(version, revision, package_versions.pop(), records, artifacts, index_digest, {'id': int(os.environ['GITHUB_RUN_ID']), 'attempt': int(os.environ['GITHUB_RUN_ATTEMPT'])}, gates)
    write_json(final / 'release-manifest.json', validate_manifest(value)); validate_bundle(final); emit_checksums(final)
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output: output.write('digest=' + index_digest + '\n')


def negative_proofs(directory, manifest):
    """Real local-bundle rejection: byte tampering and wrong source/signing identity."""
    directory = Path(directory); version = manifest['version']; revision = manifest['source_revision']; image = IMAGE + '@' + manifest['index_digest']
    for name in ('release-index.json', 'release-manifest.json', 'sbom-amd64.spdx.json'):
        with tempfile.TemporaryDirectory(prefix='openmedia-negative-') as temporary:
            target = Path(temporary)
            for path in directory.iterdir():
                if path.is_file(): os.link(path, target / path.name)
            altered = target / name; data = altered.read_bytes(); altered.unlink(); altered.write_bytes(data + b' ')
            try: verify(target, image, version, revision, default_policy())
            except (ReleaseError, subprocess.SubprocessError): pass
            else: raise ReleaseError('Tampered evidence unexpectedly verified')
    with tempfile.TemporaryDirectory(prefix='openmedia-negative-identity-') as temporary:
        environment = anonymous_environment(os.environ, temporary)
        command = ['gh', 'attestation', 'verify', str(directory / 'release-index.json'), '--bundle', str(directory / 'provenance.sigstore.json'), '--repo', REPOSITORY, '--signer-workflow', 'github.com/' + REPOSITORY + '/.github/workflows/untrusted.yml', '--format', 'json']
        try: run(command, env=environment)
        except subprocess.CalledProcessError: pass
        else: raise ReleaseError('Wrong signer unexpectedly verified')


def anonymous_images(manifest):
    with tempfile.TemporaryDirectory(prefix='openmedia-anonymous-images-') as temporary:
        environment = anonymous_environment(os.environ, temporary)
        for platform in manifest['platforms']:
            run(['docker', '--config', environment['DOCKER_CONFIG'], 'pull', '--platform', platform['platform'], IMAGE + '@' + platform['platform_digest']], env=environment)


def finalize(directory):
    version, revision = release_identity(); directory = Path(directory).resolve()
    manifest = verify(directory, IMAGE + '@' + read_json(directory / 'release-manifest.json')['index_digest'], version, revision, default_policy())
    negative_proofs(directory, manifest); anonymous_images(manifest); emit_checksums(directory)
    existing = get_release(version)
    require(existing and existing['draft'] and not existing['assets'], 'Final release is not an empty immutable staging draft')
    # Source materials remain in their already completed immutable release.
    names = [a['name'] for a in manifest['artifacts'] if '/download/' + version + '/' in a['url']]
    names += ['release-manifest.json', 'release-manifest.sigstore.json', 'provenance.sigstore.json', 'SHA256SUMS']
    run(['gh', 'release', 'upload', version, '--repo', REPOSITORY] + [str(directory / name) for name in names])
    run(['gh', 'release', 'edit', version, '--repo', REPOSITORY, '--draft=false', '--prerelease', '--latest=false'])
    published = get_release(version)
    require(published.get('immutable') is True, 'Final release was not immutable')
    # Acceptance is downstream of finalization; failure never replaces locked assets.
    with tempfile.TemporaryDirectory(prefix='openmedia-public-evidence-') as temporary:
        target = Path(temporary)
        for asset in manifest['artifacts']: download_public(asset['url'], target / asset['name'], asset)
        for name in ('release-manifest.json', 'release-manifest.sigstore.json', 'provenance.sigstore.json', 'SHA256SUMS'):
            expected = {'sha256': digest(directory / name), 'size': (directory / name).stat().st_size}
            download_public(SOURCE + '/releases/download/' + version + '/' + name, target / name, expected)
        verify(target, IMAGE + '@' + manifest['index_digest'], version, revision, default_policy())
    notes = directory / 'accepted-notes.txt'; notes.write_text('Public distribution checks passed for this preview. Deployment acceptance and inherited source/live readiness gates remain open; see the signed manifest and feature validation record. Matching source materials are retained in sources-' + version + '.\n')
    run(['gh', 'release', 'edit', version, '--repo', REPOSITORY, '--title', version + ' preview', '--notes-file', str(notes)])


def incomplete(directory):
    version, _ = release_identity(); directory = Path(directory); directory.mkdir(exist_ok=True)
    path = directory / 'incomplete-notes.txt'; path.write_text('INCOMPLETE public distribution: a post-push verification or evidence-download gate failed. Images may already be distributed. Matching sources are retained at sources-' + version + '. No acceptance claim is made; immutable artifacts will not be replaced. Inspect this Actions run and use a new version for content changes.\n')
    run(['gh', 'release', 'edit', version, '--repo', REPOSITORY, '--title', version + ' — INCOMPLETE preview', '--notes-file', str(path)])


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('command', choices=['audit-pins', 'authority', 'stage-sources', 'promote', 'finalize', 'incomplete']); parser.add_argument('--directory', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'audit-pins': audit_pins()
        else: globals()[args.command.replace('-', '_')](args.directory)
    except (ReleaseError, OSError, ValueError, KeyError, subprocess.SubprocessError):
        raise SystemExit('Release stage failed: ' + args.command + '; distribution remains incomplete') from None


if __name__ == '__main__': main()
