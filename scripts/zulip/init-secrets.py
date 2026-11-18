#!/usr/bin/env python3
"""Create one complete SD-backed credential set without replacing existing data."""

import fcntl
import getpass
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

MOUNT = Path("/srv/storage/state")
STATE = MOUNT / "services/zulip"
NAMES = ("postgres_password", "memcached_password", "rabbitmq_password",
         "redis_password", "secret_key", "email_password")


def store_secrets(password, folder=STATE / "secrets"):
    if not password or any(c in password for c in "\r\n\x00"):
        raise ValueError("A nonempty single-line SMTP password is required")
    if folder.is_symlink() or folder.resolve() != folder:
        raise ValueError("Credential storage must not be redirected")
    parent_fd = os.open(folder.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fcntl.flock(parent_fd, fcntl.LOCK_EX)
        if folder.exists() or folder.is_symlink():
            raise FileExistsError("Existing credential storage is never replaced")
        temporary = Path(tempfile.mkdtemp(prefix=".secrets-", dir=folder.parent))
        try:
            for name in NAMES:
                value = password if name == "email_password" else secrets.token_hex(32)
                with (temporary / name).open("x") as output:
                    output.write(value)
                    output.flush()
                    os.fchmod(output.fileno(), 0o444)
                    os.fsync(output.fileno())
            # Cooperating installers hold the parent lock; publish the entire set.
            os.rename(temporary, folder)
            os.fsync(parent_fd)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    finally:
        os.close(parent_fd)


def main():
    if os.geteuid() or not sys.stdin.isatty():
        sys.exit("Run with sudo in an interactive terminal; credentials are entered hidden.")
    subprocess.run(["/usr/bin/ls", "-A", str(MOUNT)], capture_output=True, check=False)
    mounted = subprocess.run([
        "/usr/bin/findmnt", "--kernel", "--mountpoint", str(MOUNT),
        "--types", "ext4", "--noheadings", "--output", "LABEL",
    ], capture_output=True, text=True, check=False)
    if mounted.returncode or mounted.stdout.strip() != "storage_sdcard":
        sys.exit("Required ext4 SD filesystem is unavailable; nothing was written.")
    if STATE.resolve() != STATE or STATE.is_symlink() or not STATE.is_dir():
        sys.exit("Run the preparation playbook first; Zulip storage is missing or redirected.")
    backing = subprocess.run([
        "/usr/bin/findmnt", "--kernel", "--target", str(STATE), "--types", "ext4",
        "--noheadings", "--output", "TARGET,LABEL",
    ], capture_output=True, text=True, check=False)
    if backing.returncode or backing.stdout.split() != [str(MOUNT), "storage_sdcard"]:
        sys.exit("Zulip storage is not on the expected SD filesystem.")
    folder = STATE / "secrets"
    if folder.exists() or folder.is_symlink():
        sys.exit("Existing credential storage preserved. Restore a partial set from backup; do not regenerate it.")
    os.umask(0o077)
    warnings.simplefilter("error", getpass.GetPassWarning)
    try:
        password = getpass.getpass("SMTP submission password (hidden): ")
        store_secrets(password, folder)
    except (OSError, ValueError, EOFError, getpass.GetPassWarning):
        sys.exit("Credentials could not be installed. No existing credential was replaced.")
    print("Zulip credentials installed. No values were printed.")


if __name__ == "__main__":
    main()
