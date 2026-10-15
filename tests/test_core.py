import hashlib
import json
import stat
import zipfile
from pathlib import Path

import pytest

from backup_restore_rehearsal.core import inspect, load_manifest, restore, safe_name


def fixture(tmp_path, entries=None, manifest=None):
    entries = (
        entries if entries is not None else {"notes/a.txt": b"synthetic fixture", "empty": b""}
    )
    source = tmp_path / "selected.zip"
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    hashes = (
        manifest
        if manifest is not None
        else {name: hashlib.sha256(data).hexdigest() for name, data in entries.items()}
    )
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({"schema": 1, "files": hashes}))
    return source, m


def test_verified_restore_new_target_preserves_inputs(tmp_path):
    source, manifest = fixture(tmp_path)
    original = source.read_bytes()
    sentinel = tmp_path / "notes"
    sentinel.write_text("existing data")
    assert inspect(source, manifest)["verified_files"] == 2
    result = restore(source, manifest, tmp_path, True)
    target = Path(result["target"])
    assert target.name.startswith("restore-rehearsal-")
    assert (target / "notes/a.txt").read_bytes() == b"synthetic fixture"
    assert sentinel.read_text() == "existing data"
    assert source.read_bytes() == original
    second = restore(source, manifest, tmp_path, True)
    assert second["target"] != str(target)


def test_requires_review_and_parent(tmp_path):
    source, m = fixture(tmp_path)
    with pytest.raises(ValueError):
        restore(source, m, tmp_path, False)
    with pytest.raises(ValueError):
        restore(source, m, tmp_path / "absent", True)


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "/root/a",
        "C:/a",
        "a\\b",
        "a//b",
        "./a",
        "NUL",
        "con.txt",
        "a.",
        "a ",
        "a:b",
        "a/../b",
        "a/\x00b",
        "a/\u0065\u0301",
        "a/" * 18 + "z",
        "a?b",
    ],
)
def test_unsafe_paths(name):
    with pytest.raises(ValueError):
        safe_name(name)


def test_manifest_mismatch_makes_no_target(tmp_path):
    source, m = fixture(tmp_path, manifest={"other": "0" * 64})
    with pytest.raises(ValueError):
        restore(source, m, tmp_path, True)
    assert not list(tmp_path.glob("restore-rehearsal-*"))


def test_symlink_member_rejected(tmp_path):
    source = tmp_path / "links.zip"
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr(info, "../../outside")
    m = tmp_path / "manifest.json"
    m.write_text(json.dumps({"schema": 1, "files": {"link": "0" * 64}}))
    with pytest.raises(ValueError, match="Symlink"):
        inspect(source, m)


def test_bomb_and_collision_rejected(tmp_path):
    source, m = fixture(tmp_path, {"large": b"x" * 100_000})
    with pytest.raises(ValueError, match="expansion"):
        inspect(source, m)
    source, m = fixture(tmp_path, {"A": b"x", "a": b"x"})
    with pytest.raises(ValueError, match="collision"):
        inspect(source, m)
    source, m = fixture(tmp_path, {"a": b"x", "a/b": b"x"})
    with pytest.raises(ValueError, match="collision"):
        inspect(source, m)


def test_duplicates_and_manifest_duplicates(tmp_path):
    source, m = fixture(tmp_path, {"a": b"x"})
    with zipfile.ZipFile(source, "a") as archive:
        archive.writestr("a", b"y")
    with pytest.raises(ValueError, match="Duplicate"):
        inspect(source, m)
    m.write_text('{"schema":1,"files":{"a":"' + "0" * 64 + '","a":"' + "0" * 64 + '"}}')
    with pytest.raises(ValueError, match="Duplicate"):
        load_manifest(m)


def test_selected_symlink_parent_rejected(tmp_path):
    source, m = fixture(tmp_path)
    link = tmp_path / "alias"
    try:
        link.symlink_to(tmp_path, target_is_directory=True)
    except OSError:
        pytest.skip("Creating symlinks requires platform permission")
    with pytest.raises(ValueError, match="Symlink"):
        restore(source, m, link, True)


def test_corrupt_and_missing_entries(tmp_path):
    source, m = fixture(tmp_path)
    source.write_bytes(b"not a zip")
    with pytest.raises(zipfile.BadZipFile):
        inspect(source, m)
