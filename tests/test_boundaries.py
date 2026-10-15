import hashlib
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from backup_restore_rehearsal import core


def selected(tmp_path, entries):
    archive = tmp_path / "selected.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as output:
        for name, data in entries.items():
            output.writestr(name, data)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "files": {name: hashlib.sha256(data).hexdigest() for name, data in entries.items()},
            }
        )
    )
    return archive, manifest


def test_crc_failure_is_detected_before_target_creation(tmp_path):
    payload = b"Unique CRC fixture payload"
    archive, manifest = selected(tmp_path, {"data.txt": payload})
    assert core.inspect(archive, manifest)["verified_files"] == 1
    archive.write_bytes(archive.read_bytes().replace(payload, b"X" + payload[1:], 1))
    with pytest.raises(zipfile.BadZipFile, match="CRC"):
        core.restore(archive, manifest, tmp_path, True)
    assert not list(tmp_path.glob("restore-rehearsal-*"))


def test_inclusive_member_total_entry_and_archive_size_boundaries(tmp_path, monkeypatch):
    archive, manifest = selected(tmp_path, {"a": b"a" * 8, "b": b"b" * 8})
    monkeypatch.setattr(core, "MAX_FILE", 8)
    monkeypatch.setattr(core, "MAX_TOTAL", 16)
    monkeypatch.setattr(core, "MAX_ENTRIES", 2)
    monkeypatch.setattr(core, "MAX_ARCHIVE", archive.stat().st_size)
    assert core.inspect(archive, manifest)["expanded_bytes"] == 16
    monkeypatch.setattr(core, "MAX_ARCHIVE", archive.stat().st_size - 1)
    with pytest.raises(ValueError):
        core.inspect(archive, manifest)
    monkeypatch.setattr(core, "MAX_ARCHIVE", 100000)
    archive, manifest = selected(tmp_path, {"a": b"a" * 9})
    with pytest.raises(ValueError, match="expansion"):
        core.inspect(archive, manifest)
    monkeypatch.setattr(core, "MAX_FILE", 16)
    archive, manifest = selected(tmp_path, {"a": b"a" * 9, "b": b"b" * 8})
    with pytest.raises(ValueError, match="expansion"):
        core.inspect(archive, manifest)
    archive, manifest = selected(tmp_path, {"a": b"a", "b": b"b", "c": b"c"})
    with pytest.raises(ValueError):
        core.inspect(archive, manifest)


def test_selected_path_reparse_attribute_is_rejected(tmp_path, monkeypatch):
    original = Path.lstat

    def metadata(path, *args, **kwargs):
        if path == tmp_path:
            return SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_file_attributes=0x400)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", metadata)
    with pytest.raises(ValueError, match="Reparse"):
        core.no_links(tmp_path)


def test_archive_dos_reparse_member_is_rejected(tmp_path):
    archive, manifest = selected(tmp_path, {"data": b"x"})
    info = zipfile.ZipInfo("data")
    info.external_attr = 0x400
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(info, b"x")
    with pytest.raises(ValueError, match="reparse"):
        core.inspect(archive, manifest)


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows junction acceptance")
def test_native_windows_junction_output_parent_is_rejected(tmp_path):
    archive, manifest = selected(tmp_path, {"data": b"x"})
    target = tmp_path / "private-target"
    target.mkdir()
    link = tmp_path / "junction"
    result = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        pytest.skip("The runner cannot create junctions")
    try:
        with pytest.raises(ValueError, match="junction|Reparse|Symlink"):
            core.restore(archive, manifest, link, True)
        assert not list(target.glob("restore-rehearsal-*"))
    finally:
        # Remove only the junction itself; never recursively traverse its target.
        link.rmdir()
