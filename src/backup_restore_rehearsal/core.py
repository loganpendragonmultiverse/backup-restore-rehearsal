"""Treat ZIP metadata, member paths and supplied manifests as hostile."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import struct
import tempfile
import unicodedata
import zipfile
import zlib
from pathlib import Path
from typing import Any

MAX_ARCHIVE = 64 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_FILE = 16 * 1024 * 1024
MAX_ENTRIES = 2000
MAX_RATIO = 100
RESERVED = re.compile(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", re.I)


def safe_name(name: str) -> str:
    if len(name) > 240 or not name or name != unicodedata.normalize("NFC", name):
        raise ValueError("Empty, overlong or non-canonical member path")
    if "\\" in name or ":" in name or name.startswith("/") or "\x00" in name:
        raise ValueError("Absolute, drive or ambiguous member path")
    parts = name.rstrip("/").split("/")
    if len(parts) > 16:
        raise ValueError("Member exceeds depth limit")
    for part in parts:
        if (
            part in ("", ".", "..")
            or part.endswith((" ", "."))
            or RESERVED.match(part)
            or any(ord(c) < 32 or c in '<>"|?*' for c in part)
        ):
            raise ValueError("Unsafe or non-portable member path")
    return "/".join(parts)


def no_links(path: Path) -> Path:
    absolute = path.absolute()
    for node in (absolute, *absolute.parents):
        if node.is_symlink() or (hasattr(node, "is_junction") and node.is_junction()):
            raise ValueError("Symlinks and junctions in selected paths are refused")
        if node.exists() and getattr(node.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Reparse points are refused")
    return absolute


def load_manifest(path: Path) -> dict[str, str]:
    no_links(path)
    if not path.is_file() or path.stat().st_size > 1_000_000:
        raise ValueError("Select one regular manifest file up to 1 MB")

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate manifest key")
            result[key] = value
        return result

    value = json.loads(path.read_text("utf-8"), object_pairs_hook=pairs)
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "files"}
        or type(value["schema"]) is not int
        or value["schema"] != 1
    ):
        raise ValueError("Expected schema 1 manifest with files object")
    files = value["files"]
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_ENTRIES:
        raise ValueError("Expected 1..2000 manifest file entries")
    normalized = set()
    for name, sha in files.items():
        if (
            safe_name(name) != name
            or not isinstance(sha, str)
            or not re.fullmatch("[0-9a-f]{64}", sha)
        ):
            raise ValueError("Manifest needs canonical file names and lowercase SHA-256 values")
        if name.casefold() in normalized:
            raise ValueError("Manifest case collision")
        normalized.add(name.casefold())
    return dict(files)


def inventory(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    entries = archive.infolist()
    if not entries or len(entries) > MAX_ENTRIES:
        raise ValueError("Expected 1..2000 ZIP entries")
    seen: set[str] = set()
    files: set[str] = set()
    paths = []
    total = 0
    for item in entries:
        if item.orig_filename != item.filename or item.external_attr & 0x400:
            raise ValueError("Ambiguous name or reparse member refused")
        name = safe_name(item.filename)
        folded = name.casefold()
        if folded in seen:
            raise ValueError("Duplicate or case-colliding ZIP member")
        seen.add(folded)
        paths.append(folded)
        mode = item.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if kind not in (0, stat.S_IFDIR if item.is_dir() else stat.S_IFREG):
            raise ValueError("Symlink or special ZIP member refused")
        if item.flag_bits & 1 or item.compress_type not in (
            zipfile.ZIP_STORED,
            zipfile.ZIP_DEFLATED,
        ):
            raise ValueError("Encrypted or unsupported compression")
        if item.is_dir():
            if item.file_size:
                raise ValueError("Directory entry has payload")
            continue
        files.add(folded)
        total += item.file_size
        if (
            item.file_size > MAX_FILE
            or total > MAX_TOTAL
            or item.file_size / max(item.compress_size, 1) > MAX_RATIO
        ):
            raise ValueError("Archive expansion limit exceeded")
    for name in paths:
        parts = name.split("/")
        if any("/".join(parts[:i]) in files for i in range(1, len(parts))):
            raise ValueError("File and directory path collision")
    return entries


def verify_compressed_stream(archive: zipfile.ZipFile, item: zipfile.ZipInfo) -> None:
    """Verify the complete declared compressed span, without trusting decoded size.

    ZipExtFile limits returned data to file_size. A corrupt header can otherwise
    hide decoded suffixes or an unfinished deflate stream behind a matching prefix.
    Call only after ZipFile.open has validated the local name/header and overlap.
    Output allocation is bounded to one 64 KiB chunk (including a probe byte).
    """
    source = archive.fp
    if source is None or not 0 <= item.compress_size <= MAX_ARCHIVE:
        raise zipfile.BadZipFile("Invalid compressed member extent")
    source.seek(item.header_offset + 26)
    lengths = source.read(4)
    if len(lengths) != 4:
        raise zipfile.BadZipFile("Truncated local ZIP header")
    name_bytes, extra_bytes = struct.unpack("<HH", lengths)
    source.seek(item.header_offset + 30 + name_bytes + extra_bytes)
    remaining = item.compress_size
    count = crc = 0
    decoder = (
        zlib.decompressobj(-zlib.MAX_WBITS) if item.compress_type == zipfile.ZIP_DEFLATED else None
    )
    while remaining:
        chunk = source.read(min(65536, remaining))
        if not chunk:
            raise zipfile.BadZipFile("Truncated compressed member")
        remaining -= len(chunk)
        pending = chunk
        while pending:
            if decoder is None:
                decoded, pending = pending, b""
            else:
                allowance = min(MAX_FILE, item.file_size) - count
                try:
                    decoded = decoder.decompress(pending, min(65536, allowance + 1))
                except zlib.error as error:
                    raise zipfile.BadZipFile("Invalid deflate member") from error
                pending = decoder.unconsumed_tail
                if decoder.unused_data or decoder.eof and (pending or remaining):
                    raise zipfile.BadZipFile("Trailing compressed member data")
            count += len(decoded)
            if count > min(MAX_FILE, item.file_size):
                raise ValueError("Member exceeds declared size or limit")
            crc = zlib.crc32(decoded, crc)
    if decoder is not None and not decoder.eof:
        raise zipfile.BadZipFile("Incomplete deflate stream")
    if count != item.file_size:
        raise zipfile.BadZipFile("Decoded member size differs from declaration")
    if crc != item.CRC:
        raise zipfile.BadZipFile("Bad CRC-32 for complete member")


def read_member(archive: zipfile.ZipFile, item: zipfile.ZipInfo, output: Any = None) -> str:
    count = 0
    sha = hashlib.sha256()
    with archive.open(item) as stream:
        verify_compressed_stream(archive, item)
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            count += len(chunk)
            if count > min(MAX_FILE, item.file_size):
                raise ValueError("Member exceeds declared size or limit")
            sha.update(chunk)
            if output is not None:
                output.write(chunk)
    if count != item.file_size:
        raise ValueError("Truncated ZIP member")
    return sha.hexdigest()


def verify(archive: zipfile.ZipFile, expected: dict[str, str]) -> dict[str, Any]:
    entries = inventory(archive)
    actual = {}
    for item in entries:
        digest = read_member(archive, item)
        if not item.is_dir():
            actual[item.filename] = digest
    if actual != expected:
        raise ValueError("Manifest mismatch: names or SHA-256 differ")
    return dict(
        schema=1,
        verified_files=len(actual),
        expanded_bytes=sum(item.file_size for item in entries),
        files=actual,
        limits=dict(
            entries=MAX_ENTRIES, total_bytes=MAX_TOTAL, file_bytes=MAX_FILE, ratio=MAX_RATIO
        ),
    )


def open_archive(path: Path) -> zipfile.ZipFile:
    no_links(path)
    if path.stat().st_size > MAX_ARCHIVE or not path.is_file():
        raise ValueError("Select one regular ZIP file up to 64 MiB")
    return zipfile.ZipFile(path)


def inspect(source: Path, manifest: Path) -> dict[str, Any]:
    expected = load_manifest(manifest)
    with open_archive(source) as archive:
        return verify(archive, expected)


def restore(source: Path, manifest: Path, parent: Path, reviewed: bool) -> dict[str, Any]:
    if type(reviewed) is not bool or not reviewed:
        raise ValueError("Inspect and review before --reviewed restore")
    parent = no_links(parent)
    if not parent.is_dir():
        raise ValueError("Choose an existing disposable-output parent directory")
    expected = load_manifest(manifest)
    with open_archive(source) as archive:
        report = verify(archive, expected)
        # A random, exclusively created child is the only supported restore target.
        target = Path(tempfile.mkdtemp(prefix="restore-rehearsal-", dir=parent))
        try:
            for item in archive.infolist():
                destination = target.joinpath(*safe_name(item.filename).split("/"))
                if item.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
                with os.fdopen(os.open(destination, flags, 0o600), "wb") as output:
                    sha = read_member(archive, item, output)
                if sha != expected[item.filename]:
                    raise ValueError("Archive changed during restoration")
            # Verify actual restored bytes, not just the stream supplied to write().
            restored = {}
            for name in expected:
                path = no_links(target.joinpath(*name.split("/")))
                restored[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            if restored != expected:
                raise ValueError("Restored file verification failed")
        except Exception as error:
            raise ValueError(
                f"Rehearsal failed; partial disposable target retained: {target}"
            ) from error
    return dict(**report, target=str(target), result="verified-disposable-copy")
