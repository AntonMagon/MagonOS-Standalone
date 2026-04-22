#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _redirect_streams(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    stdin_fd = os.open("/dev/null", os.O_RDONLY)
    log_fd = os.open(str(log_path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(stdin_fd, 0)
    os.dup2(log_fd, 1)
    os.dup2(log_fd, 2)
    os.close(stdin_fd)
    os.close(log_fd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Daemonize and exec a command detached from the parent shell.")
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--pid-file", required=True)
    parser.add_argument("--log-file", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("detached command is required")

    first_child = os.fork()
    if first_child > 0:
        return 0

    os.setsid()
    second_child = os.fork()
    if second_child > 0:
        os._exit(0)

    os.chdir(args.cwd)
    _redirect_streams(Path(args.log_file))
    Path(args.pid_file).write_text(str(os.getpid()), encoding="utf-8")
    # RU: Detached runtime должен стартовать как отдельный daemon-process, иначе backend/web снова умирают вместе с launcher shell.
    os.execvpe(command[0], command, os.environ.copy())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
