"""Observable release decisions, including failure after immutable publication."""
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/release'))
import validate_release as release


def authority(**changes):
    result = {'repository': 'hman-pro/openmedia', 'repository_id': 1380348601,
              'version': 'v0.1.0-preview.1', 'revision': 'a'*40,
              'source_revision': 'a'*40, 'event': 'push', 'ref_type': 'tag',
              'actor_permission': 'admin', 'tag_rules_verified': True,
              'version_exists': False, 'immutable_releases': True}
    result.update(changes)
    return result


@pytest.mark.parametrize('changes', [ {'repository': 'fork/openmedia'}, {'repository_id': 7}, {'version': 'sources-v0.1.0-preview.1'}, {'source_revision': 'b'*40}, {'event': 'pull_request'}, {'actor_permission': 'read'}, {'tag_rules_verified': False}, {'version_exists': True}, {'immutable_releases': False}])
def test_publisher_authorization_rejects_before_write(changes):
    with pytest.raises(release.ReleaseError): release.authorize_publication(authority(**changes))


def test_publisher_authorization_accepts_new_preview():
    release.authorize_publication(authority())


@pytest.mark.parametrize('failed', ['authority', 'pins', 'controlled', 'amd64', 'arm64', 'coverage', 'sources_public', 'amd64_import', 'arm64_import'])
def test_every_pre_push_gate_prevents_all_writes(failed):
    gates = dict.fromkeys(release.PRE_PUSH_GATES, True); gates[failed] = False
    writes = []
    with pytest.raises(release.ReleaseError): release.require_pre_push(gates, lambda: writes.append('push'))
    assert writes == []


@pytest.mark.parametrize('stage,expected', [('images_published', 'draft_incomplete'), ('release_finalized', 'finalized_incomplete')])
def test_failure_retains_sources_and_immutable_artifacts(stage, expected):
    assert release.failure_state(stage) == {'state': expected, 'retain_sources': True, 'replace_assets': False, 'accepted': False}


def test_local_verifier_scrubs_inherited_authentication():
    environment = release.anonymous_environment({'PATH': '/bin', 'GH_TOKEN': 'sentinel', 'GITHUB_TOKEN': 'sentinel', 'GH_ENTERPRISE_TOKEN': 'sentinel', 'DOCKER_AUTH_CONFIG': 'sentinel'}, '/tmp/empty')
    assert 'sentinel' not in str(environment)
    assert environment['GH_CONFIG_DIR'].startswith('/tmp/empty')


def test_untrusted_certificate_repository_id_rejected():
    policy = release.default_policy()
    cert = {'sourceRepositoryIdentifier': '7'}
    with pytest.raises(release.ReleaseError): release.check_verified_attestations([{'verificationResult': {'signature': {'certificate': cert}}}], policy, 'v0.1.0-preview.1', 'a'*40, 'a'*64)


def verified_result():
    import json
    return json.loads((ROOT / 'tests/fixtures/release/policy/verified-certificate.json').read_text())


def test_complete_verified_certificate_baseline():
    release.check_verified_attestations(verified_result(), release.default_policy(), 'v0.1.0-preview.1', 'a'*40, 'a'*64)


@pytest.mark.parametrize('field,changed,reason', [
    ('sourceRepositoryIdentifier','7','numeric'),
    ('sourceRepositoryURI','https://github.com/other/project','repository URI'),
    ('sourceRepositoryDigest','b'*40,'source revision/ref'),
    ('sourceRepositoryRef','refs/tags/v0.1.0-preview.2','source revision/ref'),
    ('subjectAlternativeName','https://github.com/hman-pro/openmedia/.github/workflows/other.yml@refs/tags/v0.1.0-preview.1','workflow/issuer'),
    ('issuer','https://untrusted.invalid','workflow/issuer'),
    ('runnerEnvironment','self-hosted','builder'),
])
def test_each_certificate_identity_field_is_enforced(field, changed, reason):
    result = verified_result(); result[0]['verificationResult']['signature']['certificate'][field] = changed
    with pytest.raises(release.ReleaseError, match=reason):
        release.check_verified_attestations(result, release.default_policy(), 'v0.1.0-preview.1', 'a'*40, 'a'*64)


@pytest.fixture
def signed_boundary(tmp_path, monkeypatch):
    import json, copy, subprocess
    sys.path.insert(0, str(ROOT / 'tests/fixtures/release'))
    from build_bundle import bundle
    manifest = bundle(tmp_path)
    trusted = {name: release.digest(tmp_path / name) for name in ('release-index.json','release-manifest.json')}
    calls = []
    def verifier(command, **kwargs):
        calls.append((command, kwargs))
        if command == ['gh','--version']: return 'gh version 2.103.3 (2026-10-27)\n'
        path = Path(command[3])
        if release.digest(path) != trusted[path.name]: raise subprocess.CalledProcessError(1, command, stderr='injected signature mismatch')
        result = verified_result()
        result[0]['verificationResult']['statement']['subject'][0]['digest']['sha256'] = trusted[path.name]
        result[0]['verificationResult']['statement']['subject'][0]['name'] = release.IMAGE if path.name == 'release-index.json' else 'release-manifest.json'
        return json.dumps(result)
    monkeypatch.setattr(release,'run',verifier)
    monkeypatch.setenv('GH_TOKEN','SENTINEL-AUTH'); monkeypatch.setenv('GITHUB_TOKEN','SENTINEL-AUTH'); monkeypatch.setenv('DOCKER_AUTH_CONFIG','SENTINEL-AUTH')
    return tmp_path, manifest, calls


def test_operator_verifies_raw_index_and_manifest_with_local_bundles_and_no_auth(signed_boundary):
    root, manifest, calls = signed_boundary
    release.verify(root, release.IMAGE+'@'+manifest['index_digest'], manifest['version'], manifest['source_revision'], release.default_policy())
    commands = [command for command,kwargs in calls if command[:3] == ['gh','attestation','verify']]
    assert [Path(c[3]).name for c in commands] == ['release-index.json','release-manifest.json']
    for command,kwargs in calls:
        assert 'SENTINEL-AUTH' not in str(kwargs['env'])
        assert '--custom-trusted-root' not in command
    assert all('--bundle' in c and '--deny-self-hosted-runners' in c for c in commands)
    assert not any('oci://' in part for c in commands for part in c)


@pytest.mark.parametrize('name', ['release-index.json','release-manifest.json','sbom-amd64.spdx.json'])
def test_operator_tamper_rejection_through_verifier_boundary(signed_boundary, name):
    root, manifest, calls = signed_boundary
    import subprocess
    (root/name).write_bytes((root/name).read_bytes()+b' ')
    with pytest.raises((release.ReleaseError, subprocess.CalledProcessError)):
        release.verify(root, release.IMAGE+'@'+manifest['index_digest'], manifest['version'], manifest['source_revision'], release.default_policy())


def test_release_cannot_supply_custom_trust_roots(signed_boundary):
    root, manifest, calls = signed_boundary
    policy = release.default_policy(); policy['trusted_root'] = str(root/'attacker-root.json')
    with pytest.raises(release.ReleaseError, match='Unsupported trust'):
        release.verify(root, release.IMAGE+'@'+manifest['index_digest'], manifest['version'], manifest['source_revision'], policy)
    assert calls == []


def saved_image(path, arch, version, revision):
    import json, io, tarfile, hashlib
    config = json.dumps({'os':'linux','architecture':arch,'config':{'Labels':{'org.opencontainers.image.version':version,'org.opencontainers.image.revision':revision}}}).encode()
    name = hashlib.sha256(config).hexdigest()+'.json'
    with tarfile.open(path,'w') as archive:
        for filename, data in [('manifest.json', json.dumps([{'Config':name,'RepoTags':['openmedia:tested-'+arch],'Layers':[]}]).encode()), (name,config)]:
            info=tarfile.TarInfo(filename); info.size=len(data); archive.addfile(info,io.BytesIO(data))
    return 'sha256:'+hashlib.sha256(config).hexdigest(), json.loads(config)


@pytest.mark.parametrize('fault', ['amd64_archive','arm64_archive','arm64_import','missing_arm64','failed_controlled','success'])
def test_real_promotion_command_boundary_checks_both_archives_before_first_push(tmp_path, monkeypatch, fault):
    import copy, json, subprocess
    import publish
    reference = json.loads((ROOT/'tests/fixtures/release/records/release.json').read_text())
    version=reference['version']; revision=reference['source_revision']
    for key,val in {'GITHUB_EVENT_NAME':'push','GITHUB_REF_TYPE':'tag','GITHUB_REF_NAME':version,'GITHUB_SHA':revision,'GITHUB_REPOSITORY':release.REPOSITORY,'GITHUB_REPOSITORY_ID':str(release.REPOSITORY_ID),'GITHUB_RUN_ID':'1','GITHUB_RUN_ATTEMPT':'1','GITHUB_OUTPUT':str(tmp_path/'output')}.items(): monkeypatch.setenv(key,val)
    for directory in ('authority','controlled','public-source-receipt','matching-sources'): (tmp_path/directory).mkdir()
    release.write_json(tmp_path/'authority/authority.json',authority())
    release.write_json(tmp_path/'controlled/controlled.json',{'result':'fail' if fault=='failed_controlled' else 'pass','source_revision':revision,'run_id':'1','run_attempt':'1'})
    (tmp_path/'matching-sources/source-manifest.json').write_text('controlled')
    release.write_json(tmp_path/'public-source-receipt/public-sources.json',{'version':version,'source_revision':revision,'immutable':True,'source_manifest_hash':release.digest(tmp_path/'matching-sources/source-manifest.json'),'assets':[]})
    configs={}; inventories=[]
    for record in reference['platforms']:
        arch=record['platform'].split('/')[1]; folder=tmp_path/('native-'+arch);folder.mkdir()
        config,metadata=saved_image(folder/('image-'+arch+'.tar'),arch,version,revision)
        record.update(image_config_id=config,archive_hash=release.digest(folder/('image-'+arch+'.tar')),archive_path='image-'+arch+'.tar',smoke_result={'result':'pass','image_config_id':config})
        configs['openmedia:tested-'+arch]=(config,metadata)
        release.write_json(folder/record['sbom']['name'],{'spdxVersion':'SPDX-2.3','packages':[{'name':'controlled'}]})
        record['sbom']['sha256'] = release.digest(folder/record['sbom']['name'])
        inventory = {'platform':record['platform'],'image_config_id':config,'version':version,'source_revision':revision,'components':[{'name':'openmedia','version':'0.1.0'}]}
        inventories.append(inventory)
        inventory_path = tmp_path/'matching-sources'/record['component_inventory']['name']
        release.write_json(inventory_path,inventory)
        record['component_inventory']['sha256'] = release.digest(inventory_path)
        release.write_json(folder/('platform-'+arch+'.json'),record)
    if fault.endswith('_archive'):
        arch=fault.split('_')[0]; (tmp_path/('native-'+arch)/('image-'+arch+'.tar')).write_bytes(b'tampered')
    if fault=='missing_arm64': (tmp_path/'native-arm64/platform-arm64.json').unlink()
    if fault=='arm64_import': configs['openmedia:tested-arm64']=('sha256:'+'f'*64,configs['openmedia:tested-arm64'][1])
    commands=[]
    def execute(command,**kwargs):
        commands.append(command)
        if command[:3]==['regctl','manifest','head']: return 'sha256:'+release.digest(tmp_path/'final/release-index.json')
        return ''
    monkeypatch.setattr(release,'run',execute);monkeypatch.setattr(publish,'run',execute)
    monkeypatch.setattr(release,'image_config',lambda image:configs[image])
    monkeypatch.setattr(publish,'validate_sources',lambda directory:{'inventories':inventories})
    monkeypatch.setattr(publish,'unused_version',lambda version:True)
    monkeypatch.setattr(publish,'audit_pins',lambda:True)
    monkeypatch.setattr(publish,'validate_bundle',lambda directory:reference)
    monkeypatch.setattr(publish,'validate_manifest',lambda value:value)
    monkeypatch.setattr(publish,'assemble_release',lambda version,revision,package,records,artifacts,index,run,gates:{**reference,'version':version,'source_revision':revision,'platforms':records,'artifacts':artifacts,'index_digest':index})
    def raw(reference,platform=None):
        if platform:
            return json.dumps({'config':{'digest':configs['openmedia:tested-'+platform.split('/')[1]][0]}}).encode()
        return b'{"controlled":"index"}'
    monkeypatch.setattr(publish,'raw_manifest',raw)
    if fault=='success':
        publish.promote(tmp_path)
        first_push=next(i for i,c in enumerate(commands) if c[:3]==['docker','image','push'])
        imports=[i for i,c in enumerate(commands) if c[:3]==['docker','image','load']]
        assert len(imports)==2 and max(imports)<first_push
        assert not any('build' in c or 'buildx' in c and 'imagetools' not in c for c in commands)
    else:
        with pytest.raises((release.ReleaseError,OSError)): publish.promote(tmp_path)
        assert not any(c[:3]==['docker','image','push'] for c in commands)


@pytest.mark.parametrize('fault', ['write_permission','unreviewed_action'])
def test_actual_workflow_audit_rejects_privilege_or_unreviewed_pin(tmp_path, fault):
    import shutil
    import publish
    shutil.copytree(ROOT/'.github',tmp_path/'.github')
    shutil.copyfile(ROOT/'Dockerfile',tmp_path/'Dockerfile')
    ci=tmp_path/'.github/workflows/ci.yml';text=ci.read_text()
    if fault=='write_permission':text=text.replace('contents: read','contents: write',1)
    else:text=text.replace('actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1','unreviewed/action@'+'a'*40)
    ci.write_text(text)
    with pytest.raises(release.ReleaseError):publish.audit_pins(tmp_path)


@pytest.mark.parametrize('fault', ['signing','image_access','public_evidence'])
def test_actual_finalization_failure_boundaries_retain_immutable_distribution(tmp_path, monkeypatch, fault):
    import json, subprocess
    import publish
    sys.path.insert(0,str(ROOT/'tests/fixtures/release'))
    from build_bundle import bundle
    manifest=bundle(tmp_path)
    for name in ('provenance.sigstore.json','release-manifest.sigstore.json'): (tmp_path/name).write_text('controlled signature boundary')
    for key,value in {'GITHUB_EVENT_NAME':'push','GITHUB_REF_TYPE':'tag','GITHUB_REF_NAME':manifest['version'],'GITHUB_SHA':manifest['source_revision'],'GITHUB_REPOSITORY':release.REPOSITORY,'GITHUB_REPOSITORY_ID':str(release.REPOSITORY_ID)}.items():monkeypatch.setenv(key,value)
    commands=[]; state={'finalized':False}
    def execute(command,**kwargs):
        commands.append(command)
        if command[:3]==['gh','release','edit'] and '--draft=false' in command:state['finalized']=True
        return ''
    def verify(*args,**kwargs):
        if fault=='signing':raise subprocess.CalledProcessError(1,['gh','attestation','verify'])
        return manifest
    def images(value):
        if fault=='image_access':raise subprocess.CalledProcessError(1,['docker','pull'])
    def download(*args,**kwargs):
        assert state['finalized'] is True
        raise release.ReleaseError('injected anonymous public evidence download failure')
    monkeypatch.setattr(publish,'run',execute);monkeypatch.setattr(publish,'verify',verify)
    monkeypatch.setattr(publish,'negative_proofs',lambda *a:None);monkeypatch.setattr(publish,'anonymous_images',images)
    monkeypatch.setattr(publish,'download_public',download)
    monkeypatch.setattr(publish,'get_release',lambda tag:{'draft':not state['finalized'],'assets':[],'immutable':state['finalized']})
    with pytest.raises((release.ReleaseError,subprocess.CalledProcessError)):publish.finalize(tmp_path)
    assert state['finalized'] is (fault=='public_evidence')
    if fault!='public_evidence':assert not any(c[:3]==['gh','release','upload'] for c in commands)
    publish.incomplete(tmp_path)
    assert not any('delete' in c or '--clobber' in c for c in commands)
    assert 'INCOMPLETE' in (tmp_path/'incomplete-notes.txt').read_text()
    assert not (tmp_path/'accepted-notes.txt').exists()


def test_same_bytes_under_wrong_authenticated_artifact_name_are_rejected():
    result = verified_result()
    result[0]['verificationResult']['statement']['subject'][0]['name'] = 'other-image'
    with pytest.raises(release.ReleaseError, match='artifact subject'):
        release.check_verified_attestations(result, release.default_policy(), 'v0.1.0-preview.1', 'a'*40, 'a'*64, release.IMAGE)
