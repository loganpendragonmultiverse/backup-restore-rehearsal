"""Frozen public-tag Windows QA transport; no source or release mutation."""

import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = "loganpendragonmultiverse/backup-restore-rehearsal"
COMMIT = "e1b9beffde6147e68679c1605ac1111263e11402"
RUN = 39528048421
ARTIFACT = 12314615017
ENVELOPE = "cc9f1aa6dda72fb16705b5bf7326328689c681e940985efd00e314473918f545"
RUNNER = "4f9e6a87595a27fb0dc7f34161b3f6c4c5805210cca5394c2419c42aaf4a870e"
ROUTING = "ca2b5aebf603383205c41e57a144c432f4b1a8ea3a2bfc3518c1a83858fe391f"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def gh(path):
    r = subprocess.run(
        ["gh", "api", "--method", "GET", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if r.returncode:
        raise RuntimeError("Read-only official artifact request failed")
    return r.stdout


def write(path, data):
    with path.open("xb") as f:
        f.write(data)


def inputs():
    assert sha((HERE / "run_backup_native.py.txt").read_bytes()) == RUNNER
    raw = (HERE / "routing.json").read_bytes()
    assert sha(raw) == ROUTING
    c = json.loads(raw)
    assert c["commit"] == COMMIT and c["tag_run"] == RUN
    return c


def main():
    mode = sys.argv[1]
    assert mode in {"download", "run"}
    assert platform.system() == "Windows" and sys.version_info[:2] in {(3, 11), (3, 14)}
    c = inputs()
    root = Path(os.environ["RUNNER_TEMP"]) / ("backup-native-" + str(sys.version_info.minor))
    artifacts = root / "artifacts"
    if mode == "download":
        assert not root.exists()
        root.mkdir()
        artifacts.mkdir()
        meta = json.loads(gh(f"repos/{REPO}/actions/artifacts/{ARTIFACT}"))
        assert meta["id"] == ARTIFACT and not meta["expired"] and meta["size_in_bytes"] == 33267
        assert meta["digest"] == "sha256:" + ENVELOPE
        assert meta["workflow_run"]["id"] == RUN and meta["workflow_run"]["head_sha"] == COMMIT
        run = json.loads(gh(f"repos/{REPO}/actions/runs/{RUN}"))
        assert (
            run["head_sha"] == COMMIT and run["head_branch"] == "v0.1.1" and run["event"] == "push"
        )
        assert (
            run["path"] == ".github/workflows/release.yml"
            and run["status"] == "completed"
            and run["conclusion"] == "success"
        )
        raw = gh(f"repos/{REPO}/actions/artifacts/{ARTIFACT}/zip")
        assert len(raw) == 33267 and sha(raw) == ENVELOPE
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            entries = z.infolist()
            assert len(entries) == 3 and {i.filename for i in entries} == set(
                c["tag_artifact_hashes"]
            )
            assert all(
                not i.is_dir() and not i.flag_bits & 1 and i.file_size < 1000000 for i in entries
            )
            for i in entries:
                data = z.read(i)
                assert sha(data) == c["tag_artifact_hashes"][i.filename]
                write(artifacts / i.filename, data)
        write(
            root / "DOWNLOAD.json",
            json.dumps(
                {
                    "artifact_id": ARTIFACT,
                    "tag_run": RUN,
                    "commit": COMMIT,
                    "container_size": len(raw),
                    "container_sha256": sha(raw),
                    "asset_hashes": c["tag_artifact_hashes"],
                    "passed": True,
                },
                indent=2,
            ).encode(),
        )
    else:
        assert not os.environ.get("GH_TOKEN") and not os.environ.get("GITHUB_TOKEN")
        source = Path(os.environ["GITHUB_WORKSPACE"]) / "tag-source"
        r = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        assert r.stdout.strip() == COMMIT
        for n, h in c["source_files"].items():
            assert sha((source / n).read_bytes()) == h, n
        for n, h in c["tag_artifact_hashes"].items():
            assert sha((artifacts / n).read_bytes()) == h, n
        pre = root / "preflight"
        assert not pre.exists()
        pre.mkdir()
        target = pre / "target"
        target.mkdir()
        (target / "value.txt").write_text("native fixture", encoding="utf-8")
        (pre / "os-symlink").symlink_to(target, target_is_directory=True)
        r = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(pre / "junction"), str(target)],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert (pre / "os-symlink/value.txt").read_text() == "native fixture" and (
            pre / "junction/value.txt"
        ).read_text() == "native fixture"
        write(
            root / "PREFLIGHT.json",
            json.dumps(
                {
                    "system": platform.system(),
                    "platform": platform.platform(),
                    "python": sys.version,
                    "os_symlink": True,
                    "junction": True,
                    "runner_sha256": RUNNER,
                    "routing_sha256": ROUTING,
                    "source_files_sha256": c["source_files_sha256"],
                    "passed": True,
                },
                indent=2,
            ).encode(),
        )
        subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(HERE / "run_backup_native.py.txt"),
                "--source",
                str(source),
                "--artifacts",
                str(artifacts),
                "--routing",
                str(HERE / "routing.json"),
                "--output",
                str(root / "acceptance"),
            ],
            check=True,
        )
        inputs()
        for n, h in c["source_files"].items():
            assert sha((source / n).read_bytes()) == h, n
        for n, h in c["tag_artifact_hashes"].items():
            assert sha((artifacts / n).read_bytes()) == h, n


if __name__ == "__main__":
    main()
