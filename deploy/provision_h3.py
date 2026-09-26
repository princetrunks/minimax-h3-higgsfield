#!/usr/bin/env python3
"""Upload and install H3 Studio on a rented Linux server running ComfyUI."""

import argparse
import getpass
import pathlib
import shlex
import sys
import uuid

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="SSH hostname or IP from your rental")
    parser.add_argument("--port", type=int, default=22, help="SSH port from your rental")
    parser.add_argument("--user", default="root", help="SSH username")
    parser.add_argument("--comfy-root", help="ComfyUI directory; detected if omitted")
    parser.add_argument("--identity", type=pathlib.Path, help="SSH private key instead of a password")
    parser.add_argument("--archive", type=pathlib.Path, default=pathlib.Path(__file__).with_name("h3-cloud-setup.zip"))
    parser.add_argument("--library-backup", type=pathlib.Path,
                        help="Optional H3 video/settings snapshot to merge into this server")
    args = parser.parse_args()
    try:
        import paramiko
    except ImportError:
        raise SystemExit("Install dependency first: python -m pip install -r requirements-installer.txt")
    archive = args.archive.resolve()
    if not archive.is_file():
        parser.error(f"Setup archive not found: {archive}")
    if args.library_backup and not args.library_backup.is_file():
        parser.error(f"Library snapshot not found: {args.library_backup}")
    password = None if args.identity else getpass.getpass("SSH password (never saved): ")
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())
    client.connect(args.host, port=args.port, username=args.user, password=password,
                   key_filename=str(args.identity.resolve()) if args.identity else None,
                   look_for_keys=False, allow_agent=False, timeout=20)
    unique = uuid.uuid4().hex[:12]
    remote_archive = f"/tmp/h3-cloud-setup-{unique}.zip"
    remote_stage = f"/tmp/h3-cloud-setup-{unique}"
    remote_library = f"/tmp/h3-library-{unique}.zip"
    try:
        with client.open_sftp() as sftp:
            sftp.put(str(archive), remote_archive)
            if args.library_backup:
                sftp.put(str(args.library_backup.resolve()), remote_library)
        root = shlex.quote(args.comfy_root) if args.comfy_root else '"$COMFY_ROOT"'
        find_root = "" if args.comfy_root else (
            'for candidate in /app/ComfyUI /workspace/ComfyUI "$HOME/ComfyUI"; do '
            'if [ -f "$candidate/main.py" ]; then COMFY_ROOT="$candidate"; break; fi; done; '
            'test -n "${COMFY_ROOT:-}" || { echo "ComfyUI not found; pass --comfy-root" >&2; exit 2; }; '
        )
        command = (
            "set -eu; " + find_root +
            f"mkdir -p {shlex.quote(remote_stage)}; "
            f"python3 -m zipfile -e {shlex.quote(remote_archive)} {shlex.quote(remote_stage)}; "
            f"bash {shlex.quote(remote_stage + '/h3-studio-src/deploy/bootstrap_h3_server.sh')} " + root
        )
        if args.library_backup:
            command += (
                "; python3 " + shlex.quote(remote_stage + "/h3-studio-src/deploy/restore_h3_library.py")
                + " --comfy-root " + root + " --archive " + shlex.quote(remote_library)
            )
        _, stdout, stderr = client.exec_command(command, get_pty=True, timeout=3600)
        for line in stdout:
            print(line, end="")
        for line in stderr:
            print(line, end="", file=sys.stderr)
        return stdout.channel.recv_exit_status()
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
