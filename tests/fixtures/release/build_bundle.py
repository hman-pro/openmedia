"""Generated controlled release materials; no real signatures or upstream software."""
import copy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts/release'))
import collect_sources
import validate_release as release


def bundle(root):
    root = Path(root)
    value = json.loads((Path(__file__).parent / 'records/release.json').read_text())
    inventories = []
    components = []
    for platform in value['platforms']:
        component = {'component_id': 'debian:fixture@1', 'kind': 'debian', 'name': 'fixture', 'version': '1', 'architectures': sorted(release.PLATFORMS), 'license': 'Controlled fixture text', 'source_identity': {'name': 'fixture', 'version': '1'}, 'source_files': [{'path': 'materials/fixture.txt', 'url': 'https://example.invalid/controlled', 'sha256': '', 'size': 7}], 'notice_paths': ['notices/fixture.txt'], 'build_materials': ['build/recipe.txt'], 'incorporated_sources': [], 'coverage': 'complete'}
        inventory = {'schema_version': 1, 'platform': platform['platform'], 'version': value['version'], 'source_revision': value['source_revision'], 'image_config_id': platform['image_config_id'], 'components': [component]}
        inventories.append(inventory)
        release.write_json(root / platform['component_inventory']['name'], inventory)
        release.write_json(root / platform['sbom']['name'], {'spdxVersion': 'SPDX-2.3', 'packages': [{'name': 'controlled-fixture'}]})
        arch = platform['platform'].split('/')[1]
        child = root / ('manifest-' + arch + '.json')
        release.write_json(child, {'schemaVersion': 2, 'config': {'digest': platform['image_config_id']}})
        platform['platform_digest'] = 'sha256:' + release.digest(child)
    for name, data in [('materials/fixture.txt', b'fixture'), ('notices/fixture.txt', b'fixture-license'), ('build/recipe.txt', b'fixture-recipe')]:
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    components = [copy.deepcopy(inventories[0]['components'][0])]
    components[0]['source_files'][0]['sha256'] = release.digest(root / 'materials/fixture.txt')
    auxiliary = {name: {'sha256': release.digest(root / name), 'size': (root / name).stat().st_size} for name in ['notices/fixture.txt', 'build/recipe.txt']}
    source = {'schema_version': 1, 'inventories': inventories, 'components': components, 'auxiliary_files': auxiliary}
    source['parts'] = collect_sources.package_parts(root, components)
    release.write_json(root / 'source-manifest.json', source)
    release.write_json(root / 'release-index.json', {'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.index.v1+json', 'manifests': [{'platform': {'os': 'linux', 'architecture': p['platform'].split('/')[1]}, 'digest': p['platform_digest']} for p in value['platforms']]})
    value['index_digest'] = 'sha256:' + release.digest(root / 'release-index.json')
    value['artifacts'] = []
    for name in ['release-index.json','source-manifest.json','manifest-amd64.json','manifest-arm64.json','sbom-amd64.spdx.json','sbom-arm64.spdx.json','inventory-amd64.json','inventory-arm64.json'] + [p['name'] for p in source['parts']]:
        path = root / name; source_asset = name.startswith(('source', 'notices', 'inventory'))
        value['artifacts'].append({'name': name, 'sha256': release.digest(path), 'size': path.stat().st_size, 'media_type': 'application/json', 'url': release.SOURCE + '/releases/download/' + ('sources-' if source_asset else '') + value['version'] + '/' + name})
    for platform in value['platforms']:
        for field in ('sbom','component_inventory'):
            platform[field]['sha256'] = release.digest(root / platform[field]['name'])
    release.write_json(root / 'release-manifest.json', value)
    release.validate_bundle(root)
    return value
