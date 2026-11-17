#!/usr/bin/env python3
"""Join a successful native smoke to the exact exported config and archive."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from validate_release import archive_config, digest, image_config, require, write_json


def record(image, platform, directory, version, revision):
    directory = Path(directory); arch = platform.split('/')[1]
    config, metadata = image_config(image)
    archive = directory / ('image-' + arch + '.tar')
    require(archive.exists(), 'Missing checked archive')
    archived, config_data = archive_config(archive)
    require(config == archived, 'Archive differs from checked image')
    inventory_file = directory / ('inventory-' + arch + '.json')
    inventory = json.loads(inventory_file.read_text())
    require(inventory['image_config_id'] == config and inventory['source_revision'] == revision and inventory['version'] == version, 'Inventory/image/source mismatch')
    labels = config_data['config']['Labels']
    require(labels['org.opencontainers.image.version'] == version and labels['org.opencontainers.image.revision'] == revision, 'Wrong checked image labels')
    bases = {m[0].lower(): m[1] for m in re.findall(r'ARG (PYTHON|UV|DENO)_IMAGE=.*@(sha256:[a-f0-9]{64})', Path('Dockerfile').read_text())}
    value = {'platform': platform, 'version': version, 'runner': {'label': 'ubuntu-24.04' + ('-arm' if arch == 'arm64' else ''), 'architecture': arch, 'image_revision': os.environ['ImageVersion']},
             'image_config_id': config, 'archive_hash': digest(archive), 'archive_path': archive.name,
             'base_digests': bases, 'tool_versions': {**inventory['tool_versions'], 'docker': subprocess.check_output(['docker', '--version'], text=True).strip(), 'buildx': subprocess.check_output(['docker', 'buildx', 'version'], text=True).strip(), 'syft': subprocess.check_output(['syft', 'version'], text=True).strip()},
             'smoke_result': {'result': 'pass', 'image_config_id': config},
             'sbom': {'name': 'sbom-' + arch + '.spdx.json', 'sha256': digest(directory / ('sbom-' + arch + '.spdx.json'))},
             'component_inventory': {'name': inventory_file.name, 'sha256': digest(inventory_file), 'version': version, 'source_revision': revision, 'platform': platform}}
    write_json(directory / ('platform-' + arch + '.json'), value)


if __name__ == '__main__':
    parser = argparse.ArgumentParser();
    for key in ('image', 'platform', 'directory', 'version', 'revision'): parser.add_argument('--' + key, required=True)
    args = parser.parse_args(); record(args.image, args.platform, args.directory, args.version, args.revision)
