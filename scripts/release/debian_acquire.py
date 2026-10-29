"""Pinned collector's authenticated APT boundary; never executes source build code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess


def command(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def fields(text):
    value = {}; key = None
    for line in text.splitlines():
        if line.startswith(' ') and key: value[key] += '\n' + line
        elif ': ' in line: key, data = line.split(': ', 1); value[key] = data
        elif line.endswith(':'): key = line[:-1]; value[key] = ''
    return value


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--name', required=True); parser.add_argument('--version', required=True); parser.add_argument('--snapshot', required=True, action='append'); parser.add_argument('--output', default='/output')
    args = parser.parse_args()
    if not re.fullmatch('[a-z0-9][a-z0-9+.-]*', args.name) or not re.fullmatch('[A-Za-z0-9.+:~_-]+', args.version) or not all(re.fullmatch('[0-9]{8}T[0-9]{6}Z', value) for value in args.snapshot): raise SystemExit('Invalid source identity')
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    # Signed current and historical indexes; expiry bypass only for frozen historical
    # metadata. No trusted=yes or AllowUnauthenticated options exist here.
    sources = f'''Types: deb-src
URIs: https://deb.debian.org/debian
Suites: bookworm bookworm-updates
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

Types: deb-src
URIs: https://deb.debian.org/debian-security
Suites: bookworm-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg

'''
    for snapshot in args.snapshot:
        sources += f'''Types: deb-src
URIs: https://snapshot.debian.org/archive/debian/{snapshot}/
Suites: bookworm bookworm-updates
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
Check-Valid-Until: no

Types: deb-src
URIs: https://snapshot.debian.org/archive/debian-security/{snapshot}/
Suites: bookworm-security
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg
Check-Valid-Until: no

'''
    Path('/etc/apt/sources.list.d/openmedia-sources.sources').write_text(sources)
    if not Path('/tmp/openmedia-apt-ready').exists():
        command(['apt-get', 'update', '-o', 'APT::Update::Error-Mode=any'])
        Path('/tmp/openmedia-apt-ready').touch()
    raw = command(['apt-cache', 'showsrc', '--only-source', args.name])
    matches = [fields(x) for x in raw.split('\n\n') if fields(x).get('Version') == args.version and fields(x).get('Package') == args.name]
    if not matches: raise SystemExit('Exact authenticated Debian source unavailable')
    metadata = matches[0]
    rows = []
    for line in metadata['Checksums-Sha256'].splitlines():
        if not line.strip(): continue
        checksum, size, name = line.split()
        if not re.fullmatch('[a-f0-9]{64}', checksum) or '/' in name or name in ('.', '..'): raise SystemExit('Invalid authenticated source metadata')
        rows.append({'name': name, 'sha256': checksum, 'size': int(size)})
    uris = command(['apt-get', 'source', '--print-uris', '--download-only', '--only-source', args.name + '=' + args.version])
    locations = {}
    for line in uris.splitlines():
        if line.startswith("'https://"):
            parts = shlex.split(line); locations[parts[1]] = parts[0]
    subprocess.run(['apt-get', 'source', '--download-only', '--only-source', args.name + '=' + args.version], cwd=output, check=True)
    for row in rows:
        path = output / row['name']
        if not path.is_file() or path.stat().st_size != row['size'] or hashlib.file_digest(path.open('rb'), 'sha256').hexdigest() != row['sha256']: raise SystemExit('APT source checksum failed')
        # APT's authenticated Directory and selected mirror identify acquisition.
        if row['name'] not in locations: raise SystemExit('Missing exact authenticated source acquisition URL')
        row['url'] = locations[row['name']]
    (output / 'authenticated-source-stanza.txt').write_text(raw)
    # Preserve exact authenticated indexes and Release signatures for audit.
    if not Path('/output/apt-authentication.tar.gz').exists():
        subprocess.run(['tar', '-czf', '/output/apt-authentication.tar.gz', '-C', '/var/lib/apt', 'lists'], check=True)
    receipt = {'source_identity': {'name': args.name, 'version': args.version}, 'files': rows,
               'snapshot': args.snapshot, 'metadata_sha256': hashlib.sha256(raw.encode()).hexdigest(),
               'collector_dpkg': command(['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\n'])}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__': main()
