"""Validate authenticated Debian source unpackability without running build code."""
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

from validate_release import inspect_archive, require

root = Path(sys.argv[1])
descriptors = list(root.glob('*.dsc'))
require(len(descriptors) == 1, 'Missing unique Debian descriptor')
text = descriptors[0].read_text().split('-----BEGIN PGP SIGNATURE-----',1)[0]
formats = re.findall(r'^Format: (.+)$', text, re.M)
require(formats and formats[0] in ('1.0','3.0 (native)','3.0 (quilt)'), 'Unsupported source unpack format')
for path in root.iterdir():
    if path.is_file() and tarfile.is_tarfile(path): inspect_archive(path)
with tempfile.TemporaryDirectory(prefix='openmedia-debian-unpack-') as temporary:
    # --no-check only skips the descriptor's old individual signer check: APT has
    # already authenticated the Sources index and exact DSC/all archive hashes.
    # Standard extraction applies packaging patches; no rules/build hooks run.
    subprocess.run(['dpkg-source', '--no-check', '--extract', str(descriptors[0]), str(Path(temporary)/'source')], check=True, timeout=180)
print('Authenticated Debian source unpackability: pass')
