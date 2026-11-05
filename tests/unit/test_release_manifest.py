"""Release identity is enforced independently from publisher availability checks."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/release'))
import validate_release as release

FIXTURES = ROOT / 'tests/fixtures/release'


def record():
    return json.loads((FIXTURES / 'records/release.json').read_text())


def test_existing_matching_release_is_valid_without_registry_query():
    value = record()
    assert release.validate_manifest(value, value['version'], value['source_revision']) == value


@pytest.mark.parametrize('field,value', [
    ('version', 'v01.2.3'), ('version', 'v1.2'), ('version', 'v1.2.3+mutable'),
    ('repository_id', 7), ('source_revision', 'abcdef'), ('package_version', ''),
    ('source_repository', 'https://github.com/other/openmedia'),
    ('source_release_tag', 'sources-v9.9.9'), ('source_release_url', 'https://evil.invalid/x'),
    ('workflow', '.github/workflows/other.yml'), ('workflow_run', {'id': 0, 'attempt': 1}),
    ('platforms', []), ('preview', False),
])
def test_manifest_rejects_wrong_or_missing_identity(field, value):
    item = record(); item[field] = value
    with pytest.raises(release.ReleaseError):
        release.validate_manifest(item)
    item = record(); del item[field]
    with pytest.raises(release.ReleaseError):
        release.validate_manifest(item)


@pytest.mark.parametrize('field', ['version', 'source_revision', 'index_digest'])
def test_published_identity_must_match_expectation(field):
    item = record(); expected = copy.deepcopy(item)
    expected[field] = 'wrong'
    with pytest.raises(release.ReleaseError):
        release.validate_manifest(item, expected['version'], expected['source_revision'], expected['index_digest'])


@pytest.mark.parametrize('mutation', ['duplicate', 'wrong_platform', 'archive_as_config', 'missing_inventory', 'stale_inventory', 'bad_url', 'cycle', 'sbom_swap'])
def test_manifest_joins_and_materials_are_checked(mutation):
    item = record(); platform = item['platforms'][0]
    if mutation == 'duplicate': item['platforms'][1] = copy.deepcopy(platform)
    if mutation == 'wrong_platform': platform['platform'] = 'linux/386'
    if mutation == 'archive_as_config': platform['image_config_id'] = platform['archive_hash']
    if mutation == 'missing_inventory': del platform['component_inventory']
    if mutation == 'stale_inventory': platform['component_inventory']['source_revision'] = 'b' * 40
    if mutation == 'bad_url': item['artifacts'][0]['url'] = 'https://github.com/other/openmedia/releases/download/v1.2.3/a'
    if mutation == 'cycle': item['artifacts'][0]['name'] = 'release-manifest.json'
    if mutation == 'sbom_swap': platform['sbom']['sha256'] = 'e' * 64
    with pytest.raises(release.ReleaseError): release.validate_manifest(item)


def test_source_coverage_requires_every_inventory_component():
    source = {'schema_version': 1, 'components': [], 'inventories': [{'components': [{'component_id': 'unmanaged:mystery'}]}]}
    with pytest.raises(release.ReleaseError): release.validate_source_manifest(source)


@pytest.fixture
def material_bundle(tmp_path):
    sys.path.insert(0, str(FIXTURES))
    from build_bundle import bundle
    value = bundle(tmp_path)
    return tmp_path, value


def test_complete_bundle_accepts_existing_immutable_identity(material_bundle):
    root, value = material_bundle
    assert release.validate_bundle(root)['index_digest'] == value['index_digest']


@pytest.mark.parametrize('mutation', ['source_bytes', 'notice_missing', 'build_missing', 'unknown_component', 'source_version', 'stale_image', 'wrong_child', 'swapped_spdx', 'index_bytes'])
def test_actual_material_joins_fail_closed(material_bundle, mutation):
    root, value = material_bundle
    if mutation in ('source_bytes', 'notice_missing', 'build_missing'):
        source = release.read_json(root / 'source-manifest.json')
        if mutation == 'source_bytes': source['components'][0]['source_files'][0]['sha256'] = 'f'*64
        if mutation == 'notice_missing': source['components'][0]['notice_paths'].append('notices/missing')
        if mutation == 'build_missing': source['components'][0]['build_materials'].append('build/missing')
        release.write_json(root / 'source-manifest.json', source)
        # Update unsigned transfer hashes; inner source/notice joins still reject.
        for asset in value['artifacts']:
            if asset['name'] == 'source-manifest.json': asset.update(sha256=release.digest(root / asset['name']), size=(root / asset['name']).stat().st_size)
        release.write_json(root / 'release-manifest.json', value)
    if mutation in ('unknown_component','source_version','stale_image'):
        inventory = release.read_json(root / 'inventory-amd64.json')
        if mutation == 'unknown_component': inventory['components'].append({'component_id':'unmanaged:unknown','version':'1'})
        if mutation == 'source_version': inventory['components'][0]['source_identity']['version'] = 'wrong'
        if mutation == 'stale_image': inventory['image_config_id'] = 'sha256:' + 'f'*64
        release.write_json(root / 'inventory-amd64.json', inventory)
    if mutation == 'wrong_child': (root / 'manifest-amd64.json').write_text('{}')
    if mutation == 'swapped_spdx': (root / 'sbom-amd64.spdx.json').write_bytes((root / 'sbom-arm64.spdx.json').read_bytes() + b' ')
    if mutation == 'index_bytes': (root / 'release-index.json').write_bytes((root / 'release-index.json').read_bytes() + b' ')
    with pytest.raises(release.ReleaseError): release.validate_bundle(root)


def test_sources_public_parts_validate_without_loose_staging(material_bundle):
    root, value = material_bundle
    import shutil
    for directory in ('materials','notices','build'): shutil.rmtree(root / directory)
    release.validate_sources(root)
    release.validate_bundle(root)


def test_final_assembly_is_pure_and_accepts_matching_existing_version():
    value = record()
    assembled = release.assemble_release(value['version'], value['source_revision'], value['package_version'], value['platforms'], value['artifacts'], value['index_digest'], value['workflow_run'], value['gates'])
    assert assembled == value
