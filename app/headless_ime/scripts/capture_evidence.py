#!/usr/bin/env python3
"""Capture a screenshot plus UI tree without bypassing privacy-window policy."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
from pathlib import Path


DEFAULT_HDC = Path("/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc")


def run(command: list[str]) -> str:
    result = subprocess.run(
        command, check=True, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--bundle")
    parser.add_argument("--serial", default="127.0.0.1:5555")
    parser.add_argument("--hdc", type=Path, default=DEFAULT_HDC)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    label = re.sub(r"[^A-Za-z0-9_.-]", "_", args.bundle or "all")
    stem = f"{stamp}-{label}"
    device_png = f"/data/local/tmp/{stem}.png"
    device_json = f"/data/local/tmp/{stem}.json"
    local_png = args.output_dir / f"{stem}.png"
    local_json = args.output_dir / f"{stem}.json"
    prefix = [str(args.hdc), "-t", args.serial]

    run([*prefix, "shell", "uitest", "screenCap", "-p", device_png])
    dump = [*prefix, "shell", "uitest", "dumpLayout", "-p", device_json]
    if args.bundle:
        dump.extend(["-b", args.bundle])
    run(dump)
    run([*prefix, "file", "recv", device_png, str(local_png.resolve())])
    run([*prefix, "file", "recv", device_json, str(local_json.resolve())])
    print(f"screenshot: {local_png.resolve()}")
    print(f"ui_tree:    {local_json.resolve()}")


if __name__ == "__main__":
    main()
