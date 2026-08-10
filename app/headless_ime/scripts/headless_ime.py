#!/usr/bin/env python3
"""Host-side controller for HmTest Headless IME."""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path


DEFAULT_HDC = Path("/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc")
KEYCODE_ENTER = "2054"
KEYCODE_DELETE = "2055"
KEYCODE_A = "2017"
KEYCODE_CTRL_LEFT = "2072"


def hdc(args: argparse.Namespace, *command: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(args.hdc), "-t", args.serial, *command], check=check, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", default="127.0.0.1:5555")
    parser.add_argument("--hdc", type=Path, default=DEFAULT_HDC)
    sub = parser.add_subparsers(dest="command", required=True)
    install = sub.add_parser("install")
    install.add_argument("hap", type=Path)
    sub.add_parser("choose")
    insert = sub.add_parser("insert")
    insert.add_argument("text")
    delete = sub.add_parser("delete")
    delete.add_argument("length", nargs="?", type=int, default=1)
    sub.add_parser("clear")
    sub.add_parser("enter")
    sub.add_parser("status")
    args = parser.parse_args()

    if args.command == "install":
        print(hdc(args, "install", "-r", str(args.hap.resolve())).stdout.strip())
    elif args.command == "choose":
        enabled = hdc(args, "shell", "ime", "-e", "com.hmtest.headlessime", "-b", check=False)
        switched = hdc(args, "shell", "ime", "-s", "com.hmtest.headlessime", check=False)
        print("\n".join(value for value in (enabled.stdout.strip(), switched.stdout.strip()) if value))
    elif args.command == "status":
        print(hdc(args, "shell", "ime", "-g").stdout.strip())
    elif args.command == "insert":
        print(hdc(args, "shell", "uitest", "uiInput", "text", args.text).stdout.strip())
    elif args.command == "delete":
        for _ in range(max(0, args.length)):
            hdc(args, "shell", "uitest", "uiInput", "keyEvent", KEYCODE_DELETE)
            time.sleep(0.08)
        print(f"Deleted {max(0, args.length)} character(s).")
    elif args.command == "clear":
        hdc(args, "shell", "uitest", "uiInput", "keyEvent", KEYCODE_CTRL_LEFT, KEYCODE_A)
        time.sleep(0.15)
        hdc(args, "shell", "uitest", "uiInput", "keyEvent", KEYCODE_DELETE)
        print("Cleared focused editor.")
    elif args.command == "enter":
        print(hdc(args, "shell", "uitest", "uiInput", "keyEvent", KEYCODE_ENTER).stdout.strip())


if __name__ == "__main__":
    main()
