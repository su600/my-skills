#!/usr/bin/env python3
"""Run a remote command on the user's Aliyun host without exposing its password in argv/env."""
import argparse
import os
from pathlib import Path
import stat
import subprocess
import sys

CREDENTIAL_FILE = Path(os.environ.get(
    "ALIYUN_CREDENTIAL_FILE",
    Path.home() / ".config" / "aliyun" / "ssh-credentials",
))


def read_credentials():
    info = CREDENTIAL_FILE.stat()
    if info.st_uid != os.getuid():
        raise RuntimeError("Credential file is not owned by the current user")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise RuntimeError("Credential file must be private (restrict permissions to owner only)")
    lines = CREDENTIAL_FILE.read_text(encoding="utf-8").splitlines()
    lines = [line.strip() for line in lines if line.strip()]
    if len(lines) != 2:
        raise RuntimeError("Expected two non-empty lines: host, then SSH password")
    host, password = lines
    if not host or not password or any(ch.isspace() for ch in host):
        raise RuntimeError("Credential file must contain a host and non-empty password")
    return host, password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-p", "--port", type=int, default=22, help="SSH port (default: 22)")
    parser.add_argument("-i", "--identity-file", help="Use SSH key authentication instead of password auth")
    parser.add_argument("--forward-stdin", action="store_true", help="Forward this process's stdin to the remote command")
    parser.add_argument("-o", "--ssh-option", action="append", default=[], metavar="KEY=VALUE",
                        help="Additional SSH option (repeatable)")
    parser.add_argument("remote_command", nargs=argparse.REMAINDER,
                        help="Remote command; separate it from options with --")
    args = parser.parse_args()
    command = args.remote_command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("provide a remote command after --")

    try:
        host, password = read_credentials()
    except (OSError, RuntimeError) as error:
        print(f"aliyun_ssh: {error}", file=sys.stderr)
        return 2

    ssh = ["ssh", "-p", str(args.port), "-o", "BatchMode=no",
           "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=10",
           "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=2"]
    for option in args.ssh_option:
        if "=" not in option:
            parser.error("--ssh-option must have the form KEY=VALUE")
        key, value = option.split("=", 1)
        if not key or not value:
            parser.error("--ssh-option must have a non-empty KEY and VALUE")
        ssh += ["-o", f"{key}={value}"]
    if args.identity_file:
        ssh += ["-i", args.identity_file, "-o", "BatchMode=yes"]
        ssh_command = ssh + [f"root@{host}"] + command
        return subprocess.run(ssh_command, check=False).returncode

    pass_fds = ()
    read_fd = write_fd = None
    try:
        read_fd, write_fd = os.pipe()
        os.set_inheritable(read_fd, True)
        sshpass = ["sshpass", "-d", str(read_fd), "ssh"] + ssh[1:]
        ssh_command = sshpass + [f"root@{host}"] + command
        child = subprocess.Popen(ssh_command, pass_fds=(read_fd,), stdin=None if args.forward_stdin else subprocess.DEVNULL)
        os.close(read_fd)
        read_fd = None
        with os.fdopen(write_fd, "w", encoding="utf-8", closefd=True) as stream:
            write_fd = None
            stream.write(password + "\n")
        return child.wait()
    except FileNotFoundError as error:
        print(f"aliyun_ssh: required executable not found: {error.filename}", file=sys.stderr)
        return 127
    except BrokenPipeError:
        return 255
    finally:
        for fd in (read_fd, write_fd):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass


if __name__ == "__main__":
    raise SystemExit(main())
