# Controlled release fixtures

`records/release.json` is entirely synthetic: repeated-digit hashes, run 1, and fake
native image identities exercise schema and joins. `sources/dpkg.tsv` deliberately
separates binary `1.0-1+b1` from source `1.0-1` and adds a Built-Using edge. It is not
an upstream package sample or an inventory of a real image.

`policy/verified-certificate.json` follows the authenticated JSON shape actually
returned by pinned GitHub CLI 2.103.3 for its original upstream signed demo fixture.
Repository, source, workflow, subject and run fields are rewritten to controlled values;
it contains no real signature and proves no OpenMedia provenance. Tests first accept
this complete baseline, then change individual identity fields. Actual Sigstore
verification is injected at the command boundary, while production invokes pinned gh
with established roots/local bundles and removes inherited authentication.

`build_bundle.py` generates complete tiny material parts and their hashes for controlled
source/notices/build/SBOM/config joins. Its fixture-license strings are synthetic test
data, not legal notices for distributed components. Safe/unsafe archives are created
in isolated pytest temporary directories. No credentials, real chat/source identifiers,
live manifests or user media are present. Real release bundles and anonymous distribution
remain feature 008 T062 acceptance gates.
