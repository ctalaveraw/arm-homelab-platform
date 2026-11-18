#!/usr/bin/env python3
"""Install a tunnel token without exposing it in argv, environment or output."""

import argparse
import getpass
import os
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

MOUNT = Path("/srv/storage/state")
TOKEN = MOUNT / "services/cloudflared/tunnel-token"


def store_token(value, path=TOKEN, replace=False):
    """Write atomically; refuse accidental replacement and redirected paths."""
    if not value or not value.isascii() or any(c.isspace() for c in value) or "\x00" in value:
        raise ValueError("Enter a nonempty single-line tunnel token.")
    if path.parent.resolve() != path.parent or path.is_symlink():
        raise ValueError("Credential storage must not use redirected paths.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chown(path.parent, 0, 0)
    path.parent.chmod(0o700)
    fd, temporary = tempfile.mkstemp(prefix=".tunnel-token-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            output.write(value)
            output.flush()
            os.fchown(output.fileno(), 0, 65532)
            os.fchmod(output.fileno(), 0o440)
            os.fsync(output.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="Replace after rotating the token in Cloudflare")
    args = parser.parse_args()
    if os.geteuid() != 0:
        sys.exit("Run this helper through sudo.")
    if not sys.stdin.isatty():
        sys.exit("Run interactively; the token must not be supplied in a command or pipe.")
    mounted = subprocess.run([
        "/usr/bin/findmnt", "--kernel", "--mountpoint", str(MOUNT),
        "--types", "ext4", "--noheadings", "--output", "LABEL",
    ], capture_output=True, text=True, check=False)
    if mounted.returncode or mounted.stdout.strip() != "storage_sdcard":
        sys.exit("Expected SD filesystem is unavailable; no credential was written.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            value = getpass.getpass("Cloudflare tunnel token (hidden): ")
        store_token(value, replace=args.replace)
    except FileExistsError:
        sys.exit("A token already exists. Use --replace only after intentional rotation.")
    except (OSError, ValueError, getpass.GetPassWarning):
        sys.exit("Token installation failed; verify storage, permissions and single-line input.")
    print("Tunnel token installed. Its value was not printed.")


if __name__ == "__main__":
    main()
