#!/usr/bin/env python3
"""Install build-only reviewed tools after verifying official asset SHA256 pins."""
import argparse
import hashlib
import io
import os
from pathlib import Path
import platform
import tarfile
from urllib.request import urlopen

PINS = {
    'buildx': ('docker/buildx', 'v0.38.1', 'buildx-v0.38.1.linux-{arch}', {'amd64': 'e25d5cd675092bb5d1d03632fdc46cdf3fede7b514dc5f023a105e00d3ce5ad4', 'arm64': '3b83b3731916ba433feccaaa689fe5bcdc81c641d92c8e6c2ea865dfa141c97a'}),
    'syft': ('anchore/syft', 'v1.55.0', 'syft_1.55.0_linux_{arch}.tar.gz', {'amd64': 'bb65249542db5fedeeb4d3f9b018b75e7264dbfbbb10486f044581a92f90490d', 'arm64': '929bd163db2d7cd2255d3bcb8967208079813d7b46b0c952f7b794d8e2c7d304'}),
    'regctl': ('regclient/regclient', 'v0.11.7', 'regctl-linux-{arch}', {'amd64': '3737fbbdd791e04e7a831640b681f3397a376498e80e2ad9b1b2d27296f239bc', 'arm64': '9f349bab5c407ac04f3dabf99c7c7a6b0f9e9723c23f2775380e804d02c6dbb9'}),
    'gh': ('cli/cli', 'v2.103.3', 'gh_2.103.3_linux_{arch}.tar.gz', {'amd64': '4c806978ffce1cec70853302a56d70ac6da4f19bae7adca4e1a8ab00633dd91d', 'arm64': 'ee32df2323c8847f5fac6cb6b4b69ca75828e9329a8f22f677021f7b3306ce63'})}


def install(tool, architecture, output):
    repository, version, template, checksums = PINS[tool]
    name = template.format(arch=architecture)
    with urlopen('https://github.com/' + repository + '/releases/download/' + version + '/' + name, timeout=120) as response: data = response.read()
    if hashlib.sha256(data).hexdigest() != checksums[architecture]: raise SystemExit('Tool checksum mismatch')
    if name.endswith('.tar.gz'):
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            matches = [m for m in archive if m.isfile() and (m.name == tool or m.name.endswith('/bin/' + tool))]
            if len(matches) != 1: raise SystemExit('Ambiguous tool asset')
            data = archive.extractfile(matches[0]).read()
    target = output / ('docker-buildx' if tool == 'buildx' else tool); target.write_bytes(data); target.chmod(0o755)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True); parser.add_argument('tools', nargs='+', choices=PINS)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    architecture = {'x86_64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}.get(platform.machine())
    if os.uname().sysname != 'Linux' or architecture is None: raise SystemExit('Use the reviewed Linux tools on a native Linux host')
    for tool in args.tools: install(tool, architecture, args.output)
