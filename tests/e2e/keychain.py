"""Credential lookup for the e2e suite: environment first, then the OS keyring.

Nothing here is written to disk or printed. Values are read per run and stay in process
memory, matching the project rule that credentials live in the OS keyring and are scoped to
the process that needs them.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess

# Keyring account and services. The account groups the items; each service is one value.
KEYRING_ACCOUNT = "openmedia-e2e"
API_ID = "openmedia-e2e-tg-api-id"
API_HASH = "openmedia-e2e-tg-api-hash"
SESSION = "openmedia-e2e-tg-session"
BOT_USERNAMES = {
    "dev": "openmedia-e2e-dev-bot-username",
    "prod": "openmedia-e2e-bot-username",
}


def _env_name(service: str) -> str:
    return service.upper().replace("-", "_")


def lookup(service: str) -> str | None:
    """Return the value for `service`, or None when it is not configured anywhere."""
    value = os.environ.get(_env_name(service))
    if value:
        return value
    if platform.system() == "Darwin" and shutil.which("security"):
        done = subprocess.run(
            ["security", "find-generic-password", "-a", KEYRING_ACCOUNT, "-s", service, "-w"],
            capture_output=True, text=True, check=False,
        )
        return (done.stdout.strip() or None) if done.returncode == 0 else None
    if shutil.which("secret-tool"):
        done = subprocess.run(["secret-tool", "lookup", "service", service],
                              capture_output=True, text=True, check=False)
        return (done.stdout.strip() or None) if done.returncode == 0 else None
    return None


def store(service: str, secret: str) -> None:
    """Store `secret` in the OS keyring without putting it in argv."""
    if platform.system() == "Darwin":
        if '"' in secret or "\n" in secret:
            raise ValueError("unsupported character in secret")
        command = f'add-generic-password -U -a {KEYRING_ACCOUNT} -s {service} -w "{secret}"\n'
        subprocess.run(["security", "-i"], input=command, text=True, capture_output=True, check=True)
        return
    subprocess.run(["secret-tool", "store", f"--label=OpenMedia e2e {service}", "service", service],
                   input=secret, text=True, capture_output=True, check=True)
