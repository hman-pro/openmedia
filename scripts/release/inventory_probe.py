"""Nonpolling image inventory, run with no network and a read-only root."""
import base64
import hashlib
import importlib.metadata
import json
import os
import re
from pathlib import Path
import subprocess
import sys


def execute(args):
    return subprocess.check_output(args, text=True).rstrip('\n')


def notices(paths):
    result = {}
    for path in paths:
        path = Path(path)
        if path.is_file():
            resolved = path.resolve()
            result[str(path)] = base64.b64encode(resolved.read_bytes()).decode('ascii')
    return result


def python_inventory():
    result = []
    for dist in importlib.metadata.distributions():
        files = list(dist.files or [])
        notice = [dist.locate_file(p) for p in files if any(word in str(p).lower() for word in ('license', 'copying', 'notice', 'copyright', 'authors'))]
        metadata = dist.metadata
        result.append({'name': metadata['Name'], 'version': dist.version,
                       'license': metadata.get('License-Expression') or metadata.get('License') or 'License texts in archived distribution',
                       'notices': notices(notice), 'files': [str(dist.locate_file(p)) for p in files]})
    return sorted(result, key=lambda x: x['name'])


if '--python-only' in sys.argv:
    print(json.dumps(python_inventory())); raise SystemExit

application = json.loads(execute(['/app/.venv/bin/python', '/probe/inventory_probe.py', '--python-only']))
system = python_inventory()
owned = {path for dist in application + system for path in dist.pop('files')}
dpkg_owned = set(execute(['dpkg-query', '-L'] + execute(['dpkg-query', '-W', '-f=${binary:Package}\n']).splitlines()).splitlines())
owned.update(dpkg_owned)
packages = execute(['dpkg-query', '-W', '-f=${binary:Package}\n']).splitlines()
for package in packages:
    for extension in ('preinst', 'postinst', 'prerm', 'postrm', 'config'):
        owned.add('/var/lib/dpkg/info/' + package + '.' + extension)
owned.update(str(Path(p).resolve()) for p in list(owned) if p.startswith("/"))
unmanaged = []
def walk_error(error):
    raise error

for directory, directories, filenames in os.walk('/', followlinks=False, onerror=walk_error):
    if directory == '/':
        directories[:] = [d for d in directories if d not in ('proc', 'sys', 'dev', 'probe')]
    for filename in filenames:
        path = Path(directory) / filename
        if not path.is_file() or path.is_symlink() or str(path) in owned or str(path.resolve()) in owned:
            continue
        with path.open('rb') as stream: magic = stream.read(4)
        if magic == b'\x7fELF' or (magic.startswith(b'#!') and path.stat().st_mode & 0o111):
            data = path.read_bytes()
            unmanaged.append({'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'rustc_revisions': sorted({x.decode() for x in re.findall(rb'/rustc/([a-f0-9]{40})/', data)})})
result = {'dpkg': execute(['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\t${Built-Using}\n']),
          'application_python': application, 'system_python': system,
          'unmanaged_files': unmanaged,
          'notices': notices(list(Path('/usr/share/doc').glob('*/copyright')) + list(Path('/usr/share/common-licenses').glob('*')) + [Path('/usr/local/LICENSE'), Path('/app/LICENSE'), Path('/app/THIRD_PARTY_NOTICES.md'), Path('/usr/local/share/doc/openmedia/RUNTIME_NOTICES.txt.gz')]),
          'tool_versions': {key: execute(args) for key, args in {'python': ['/usr/local/bin/python', '--version'], 'uv': ['uv', '--version'], 'uvx': ['uvx', '--version'], 'deno': ['deno', '--version'], 'ffmpeg': ['ffmpeg', '-version'], 'ffprobe': ['ffprobe', '-version']}.items()}}
print(json.dumps(result))
