"""User-selected ZIP and manifest only; no discovery or automatic backup access."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from .core import inspect, restore


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "restore"))
    parser.add_argument("archive", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--parent", type=Path)
    parser.add_argument("--reviewed", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "restore":
            if args.parent is None:
                raise ValueError("restore requires --parent")
            result = restore(args.archive, args.manifest, args.parent, args.reviewed)
        else:
            result = inspect(args.archive, args.manifest)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, NotImplementedError) as error:
        parser.exit(2, f"backup-restore-rehearsal: {error}\n")
    return 0
