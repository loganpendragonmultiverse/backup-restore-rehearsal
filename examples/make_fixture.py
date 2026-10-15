"""Create a tiny synthetic backup and matching manifest, refusing overwrite."""

import hashlib
import json
import zipfile
from pathlib import Path

payload = b"Disposable rehearsal fixture.\n"
with Path("synthetic.zip").open("xb") as output:
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("notes/example.txt", payload)
with Path("synthetic-manifest.json").open("x", encoding="utf-8") as output:
    json.dump(
        {"schema": 1, "files": {"notes/example.txt": hashlib.sha256(payload).hexdigest()}},
        output,
        indent=2,
    )
