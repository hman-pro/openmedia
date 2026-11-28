#!/usr/bin/env python3
"""Decide whether CI's source-closure job must run; standard library only.

Collecting matching sources takes about 20 minutes and only proves something when an input
that decides the third-party components changed. A release always collects, because
release.yml downloads this run's matching-sources artifact. OpenMedia's own source is a git
archive of the commit, so application changes alone cannot break resolution.
"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys

RELEASE_INPUTS = ('Dockerfile', 'uv.lock', 'pyproject.toml', 'release/', 'scripts/release/', '.github/workflows/')


def needs_sources(*, event, ref, version, base, changed):
    # Inside a reusable workflow, github.event_name is the caller's event, so a release is
    # recognized by its version input or its tag ref, never by 'workflow_call'.
    if version or ref.startswith('refs/tags/') or event == 'workflow_dispatch':
        return True
    if not base or set(base) == {'0'} or changed is None:
        return True  # a new branch, or a base commit that no longer exists (force-push)
    return any(path == entry or (entry.endswith('/') and path.startswith(entry))
        for path in changed for entry in RELEASE_INPUTS)


def changed_paths(base, head, *, cwd='.'):
    subprocess.run(['git', '-C', str(cwd), 'fetch', '--quiet', '--no-tags', '--depth=1', 'origin', base],
        check=False, capture_output=True)
    diff = subprocess.run(['git', '-C', str(cwd), 'diff', '--name-only', base, head],
        check=False, capture_output=True, text=True)
    if diff.returncode != 0:
        return None
    return sorted(line for line in diff.stdout.splitlines() if line)


def main():
    context = {'event': os.environ.get('GITHUB_EVENT_NAME', ''), 'ref': os.environ.get('GITHUB_REF', ''),
        'version': os.environ.get('RELEASE_VERSION', ''), 'base': os.environ.get('BASE_SHA', '')}
    quick = needs_sources(changed=[], **context)
    changed = [] if quick else changed_paths(context['base'], os.environ['GITHUB_SHA'])
    run = quick or needs_sources(changed=changed, **context)
    if quick: reason = 'release, dispatch or new branch'
    elif changed is None: reason = 'base commit unavailable'
    elif run: reason = 'changed: ' + ', '.join(p for p in changed if needs_sources(changed=[p], **context))
    else: reason = 'no release input changed'
    print('sources:', 'run' if run else 'skip', '(' + reason + ')')
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
        output.write('sources=' + ('true' if run else 'false') + '\n')


if __name__ == '__main__':
    sys.exit(main())
