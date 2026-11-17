#!/usr/bin/env python3
"""Assemble original tool/component notices for inclusion in the runtime image.

Materials are acquired by the same checksum-verified source policy as distribution.
No copyright holder is inferred. Original notices and source attribution lines are
preserved verbatim, deduplicated by bytes, with source paths recorded for review.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import gzip
import json
from pathlib import Path
import re
import tarfile

from collect_sources import acquire
from validate_release import read_json, write_json, digest, require


def assemble(policy, cache, output):
    cache = Path(cache); cache.mkdir(parents=True, exist_ok=True)
    materials = {}
    for component in policy['components']:
        if component['kind'] in ('debian', 'application-python', 'system-python') or component['name'].startswith('pip-vendored-'): continue
        for material in component.get('source_files', []): materials[material['sha256']] = material
    def download(item):
        checksum, material = item
        path = cache / checksum / material['url'].rsplit('/',1)[-1]
        return checksum, acquire(material, path)
    with ThreadPoolExecutor(max_workers=12) as pool: paths = dict(pool.map(download, materials.items()))
    entries = {}
    def retain(content, origin):
        checksum = hashlib.sha256(content).hexdigest()
        entry = entries.setdefault(checksum, {'content':content,'origins':set()}); entry['origins'].add(origin)
    for checksum, path in sorted(paths.items()):
        material = materials[checksum]
        if material.get('role') == 'notice':
            retain(path.read_bytes(), material['url']); continue
        if not tarfile.is_tarfile(path): continue
        with tarfile.open(path,'r:*') as archive:
            for member in archive:
                if not member.isfile(): continue
                name = member.name.lower(); basename = name.rsplit('/',1)[-1]
                license_file = any(w in basename for w in ('license','copying','copyright','notice','authors'))
                if license_file:
                    content = archive.extractfile(member).read()
                    # License source/test implementation files are not themselves
                    # legal notices; retain their actual attribution lines below.
                    if b'\x00' not in content:
                        retain(content, checksum + ':' + member.name)
                    continue
                stream = archive.extractfile(member)
                header = stream.read(min(member.size, 128*1024))
                if b'\x00' in header: continue
                # Original source notices can occur outside a LICENSE file. Retain
                # every explicit copyright line from text source headers verbatim.
                for line in header.splitlines(keepends=True):
                    if re.search(rb'copyright\s+(?:\(c\)\s*)?(?:[0-9]{4}|[A-Z])|\(c\)\s+[0-9]{4}|\xc2\xa9', line, re.I):
                        retain(line, checksum + ':' + member.name)
                if basename.startswith('cargo.toml'):
                    retain(header, checksum + ':' + member.name)
                elif basename.startswith('readme') and (b'Permission is hereby granted' in header or re.search(rb'copyright\s+\(c\)',header,re.I)):
                    retain(header, checksum + ':' + member.name)
    require(bool(entries), 'No runtime notices acquired')
    output = Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    require(output.name.endswith('.txt.gz'), 'Runtime notice output must use .txt.gz')
    with output.open('wb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as target:
        target.write(b'OpenMedia runtime third-party notices\n\nOriginal source/package notices follow. Source archives and exact acquisition hashes are recorded in release/source-policy.json. A source copyright line remains an original notice; an SPDX template remains a standard license text. Authors are never inferred to be copyright holders. Debian and installed Python notices are also retained in their original installed locations.\n')
        for checksum, entry in sorted(entries.items()):
            target.write(b'\n\n============================================================\n')
            target.write(('Source notice SHA256: '+checksum+'\nOrigins:\n'+'\n'.join(sorted(entry['origins']))+'\n\n').encode())
            target.write(entry['content'])
    with gzip.open(output,'rb') as stream: text_sha256 = hashlib.file_digest(stream,'sha256').hexdigest()
    provenance = output.parent / (output.name.removesuffix('.txt.gz') + '.provenance.json')
    write_json(provenance, {'schema_version':1,'bundle_sha256':digest(output),'text_sha256':text_sha256,'compression':'gzip','materials':[{k:v for k,v in material.items() if k in ('url','sha256','size','role')} for _,material in sorted(materials.items())],'notice_entries':len(entries),'original_source_preserved':True,'limitations':'No inferred copyright holders; standard text templates do not count as original notices. Full source and complete notice archives remain separately required.'})
    return len(entries)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--policy',required=True); parser.add_argument('--cache',required=True); parser.add_argument('--output',required=True)
    args=parser.parse_args();print(assemble(read_json(args.policy),args.cache,args.output))
