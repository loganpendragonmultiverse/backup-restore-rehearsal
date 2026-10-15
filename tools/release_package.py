"""Build checksummed release assets from the exact checkout; never publishes."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tomllib
import zipfile
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    if (root / "package.json").exists():
        metadata = json.loads((root / "package.json").read_text("utf-8"))
        version = metadata["version"]
        slug = metadata["name"]
        output = root / "release"
        output.mkdir(exist_ok=True)
        with zipfile.ZipFile(
            output / f"{slug}-v{version}-web.zip", "w", zipfile.ZIP_DEFLATED
        ) as archive:
            for file in sorted((root / "dist").rglob("*")):
                if file.is_file():
                    archive.write(file, str(file.relative_to(root / "dist")))
        subprocess.run(
            ["git", "archive", "--format=zip", f"--output={output / (slug + '-v' + version + '-source.zip')}", "HEAD"],
            check=True,
        )
    else:
        version = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))["project"]["version"]
        output = root / "dist"
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        if os.environ.get("GITHUB_REF_NAME") != "v" + version:
            raise SystemExit("Tag and package/runtime version differ")
    artifacts = [
        file for file in sorted(output.iterdir())
        if file.is_file() and file.name != "SHA256SUMS"
    ]
    if not artifacts:
        raise SystemExit("No distributable files were produced")
    sums = "".join(
        hashlib.sha256(file.read_bytes()).hexdigest() + "  " + file.name + "\n"
        for file in artifacts
    )
    (output / "SHA256SUMS").write_text(sums, encoding="utf-8")
    print(sums, end="")


if __name__ == "__main__":
    main()
