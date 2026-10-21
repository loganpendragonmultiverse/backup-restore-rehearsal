"""Real tiny ZIP streams, including malformed headers that fooled prefix checks."""

import hashlib
import json
import struct
import sys
import zipfile

import pytest

from backup_restore_rehearsal import core
from backup_restore_rehearsal.cli import main


def selected(tmp_path, data=b"AB", compression=zipfile.ZIP_DEFLATED):
    archive = tmp_path / "selected.zip"
    with zipfile.ZipFile(archive, "w", compression=compression) as output:
        output.writestr("a.txt", data)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"schema": 1, "files": {"a.txt": hashlib.sha256(data).hexdigest()}})
    )
    return archive, manifest


def declare(archive, manifest, data):
    raw = bytearray(archive.read_bytes())
    central = raw.index(b"PK\x01\x02")
    for offset in [14, central + 16]:
        struct.pack_into("<I", raw, offset, zipfile.crc32(data))
    for offset in [22, central + 24]:
        struct.pack_into("<I", raw, offset, len(data))
    archive.write_bytes(raw)
    manifest.write_text(
        json.dumps({"schema": 1, "files": {"a.txt": hashlib.sha256(data).hexdigest()}})
    )


@pytest.mark.parametrize("compression", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
def test_full_payload_cannot_be_hidden_by_a_matching_declared_prefix(tmp_path, compression):
    archive, manifest = selected(tmp_path, compression=compression)
    declare(archive, manifest, b"A")
    before = archive.read_bytes(), manifest.read_bytes()
    with pytest.raises(ValueError, match="declared"):
        core.restore(archive, manifest, tmp_path, True)
    assert not list(tmp_path.glob("restore-rehearsal-*"))
    assert (archive.read_bytes(), manifest.read_bytes()) == before


def test_corrupt_deflate_is_controlled_cli_failure_before_creation(tmp_path, monkeypatch, capsys):
    archive, manifest = selected(tmp_path)
    raw = bytearray(archive.read_bytes())
    raw[35] = 255
    archive.write_bytes(raw)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "backup-restore-rehearsal",
            "restore",
            str(archive),
            "--manifest",
            str(manifest),
            "--parent",
            str(tmp_path),
            "--reviewed",
        ],
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    assert "Invalid deflate" in capsys.readouterr().err
    assert not list(tmp_path.glob("restore-rehearsal-*"))


@pytest.mark.parametrize("schema", [True, 1.0, "1"])
def test_manifest_schema_is_an_integer_version(tmp_path, schema):
    archive, manifest = selected(tmp_path)
    value = json.loads(manifest.read_text())
    value["schema"] = schema
    manifest.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="schema"):
        core.inspect(archive, manifest)


@pytest.mark.parametrize("reviewed", ["false", 1, None])
def test_restore_requires_boolean_review_acceptance(tmp_path, reviewed):
    archive, manifest = selected(tmp_path)
    with pytest.raises(ValueError, match="review"):
        core.restore(archive, manifest, tmp_path, reviewed)
    assert not list(tmp_path.glob("restore-rehearsal-*"))


@pytest.mark.parametrize("compression", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
@pytest.mark.parametrize("data", [b"", b"x", b"a" * 65536 + b"b" * 32])
def test_complete_streams_and_chunk_boundaries_restore(tmp_path, compression, data, monkeypatch):
    # Chunk fixtures exercise bounded processing rather than the expansion-ratio policy.
    monkeypatch.setattr(core, "MAX_RATIO", 10000)
    archive, manifest = selected(tmp_path, data, compression)
    result = core.restore(archive, manifest, tmp_path, True)
    from pathlib import Path

    assert (Path(result["target"]) / "a.txt").read_bytes() == data


def test_unfinished_deflate_stream_cannot_pass_matching_crc(tmp_path):
    archive, manifest = selected(tmp_path, b"A")
    raw = bytearray(archive.read_bytes())
    central = raw.index(b"PK\x01\x02")
    compressed = struct.unpack_from("<I", raw, central + 20)[0]
    for offset in [18, central + 20]:
        struct.pack_into("<I", raw, offset, compressed - 1)
    archive.write_bytes(raw)
    with pytest.raises(zipfile.BadZipFile, match="Incomplete"):
        core.restore(archive, manifest, tmp_path, True)
    assert not list(tmp_path.glob("restore-rehearsal-*"))


def test_extra_compressed_tail_is_not_ignored(tmp_path):
    archive, manifest = selected(tmp_path, b"A")
    raw = bytearray(archive.read_bytes())
    central = raw.index(b"PK\x01\x02")
    compressed = struct.unpack_from("<I", raw, central + 20)[0]
    raw[central:central] = b"X"
    central += 1
    end = raw.index(b"PK\x05\x06")
    struct.pack_into("<I", raw, end + 16, central)
    for offset in [18, central + 20]:
        struct.pack_into("<I", raw, offset, compressed + 1)
    archive.write_bytes(raw)
    with pytest.raises(zipfile.BadZipFile, match="Trailing"):
        core.inspect(archive, manifest)


def test_data_descriptor_and_zip64_local_header_are_compatible(tmp_path):
    import io

    class Unseekable(io.BytesIO):
        def seekable(self):
            return False

        def seek(self, *args):
            raise OSError("fixture streaming ZIP output")

    output = Unseekable()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        with archive.open("a.txt", "w", force_zip64=True) as entry:
            entry.write(b"streamed synthetic data")
    source = tmp_path / "descriptor.zip"
    source.write_bytes(output.getvalue())
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": 1,
                "files": {"a.txt": hashlib.sha256(b"streamed synthetic data").hexdigest()},
            }
        )
    )
    assert core.inspect(source, manifest)["verified_files"] == 1
    assert core.restore(source, manifest, tmp_path, True)["result"] == "verified-disposable-copy"


def test_stored_declared_size_must_match_actual_span(tmp_path):
    archive, manifest = selected(tmp_path, b"AB", zipfile.ZIP_STORED)
    raw = bytearray(archive.read_bytes())
    central = raw.index(b"PK\x01\x02")
    for offset in [22, central + 24]:
        struct.pack_into("<I", raw, offset, 3)
    archive.write_bytes(raw)
    with pytest.raises(zipfile.BadZipFile, match="size"):
        core.inspect(archive, manifest)


def test_directory_entry_cannot_hide_compressed_payload(tmp_path):
    source = tmp_path / "directory-payload.zip"
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("dir/", b"hidden")
        archive.writestr("a.txt", b"A")
    raw = bytearray(source.read_bytes())
    central = raw.index(b"PK\x01\x02")
    for offset in [14, central + 16]:
        struct.pack_into("<I", raw, offset, 0)
    for offset in [22, central + 24]:
        struct.pack_into("<I", raw, offset, 0)
    source.write_bytes(raw)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"schema": 1, "files": {"a.txt": hashlib.sha256(b"A").hexdigest()}})
    )
    with pytest.raises(ValueError, match="declared"):
        core.restore(source, manifest, tmp_path, True)
    assert not list(tmp_path.glob("restore-rehearsal-*"))


def test_empty_deflated_directory_is_accepted(tmp_path):
    source = tmp_path / "empty-directory.zip"
    with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("dir/", b"")
        archive.writestr("a.txt", b"A")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"schema": 1, "files": {"a.txt": hashlib.sha256(b"A").hexdigest()}})
    )
    result = core.restore(source, manifest, tmp_path, True)
    from pathlib import Path

    assert (Path(result["target"]) / "dir").is_dir()


@pytest.mark.skipif(not hasattr(__import__("os"), "mkfifo"), reason="POSIX special file fixture")
def test_special_manifest_is_refused_without_opening(tmp_path):
    import os

    path = tmp_path / "manifest-pipe"
    os.mkfifo(path)
    with pytest.raises(ValueError, match="regular manifest"):
        core.load_manifest(path)


def test_hidden_expansion_stops_at_a_bounded_probe(tmp_path, monkeypatch):
    import zlib

    archive, manifest = selected(tmp_path, b"A" * 100000)
    declare(archive, manifest, b"AA")
    original = zlib.decompressobj
    observed = []

    class Decoder:
        def __init__(self, *args, **kwargs):
            self.actual = original(*args, **kwargs)

        def __getattr__(self, name):
            return getattr(self.actual, name)

        def decompress(self, data, max_length=0):
            result = self.actual.decompress(data, max_length)
            observed.append((max_length, len(result)))
            return result

    monkeypatch.setattr(zlib, "decompressobj", Decoder)
    with pytest.raises(ValueError, match="declared"):
        core.restore(archive, manifest, tmp_path, True)
    assert observed and all(0 < requested <= 3 and actual <= 3 for requested, actual in observed)
    assert not list(tmp_path.glob("restore-rehearsal-*"))
