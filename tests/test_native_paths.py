"""Actual Windows filesystem acceptance; skipped elsewhere, never counted as passed."""

import os
import subprocess

import pytest
from test_complete_streams import selected

from backup_restore_rehearsal import core


@pytest.mark.skipif(os.name != "nt", reason="Actual native Windows junction acceptance")
@pytest.mark.parametrize("position", ["archive", "manifest", "parent", "ancestor"])
def test_native_windows_selected_path_junction_is_refused(tmp_path, position):
    target = tmp_path / "actual"
    target.mkdir()
    archive, manifest = selected(target)
    (target / "nested").mkdir()
    link = tmp_path / "junction"
    result = subprocess.run(
        ["cmd.exe", "/c", "mklink", "/J", str(link), str(target)], capture_output=True, text=True
    )
    if result.returncode:
        pytest.skip("Runner cannot create a real junction; required native acceptance unavailable")
    source = link / archive.name if position == "archive" else archive
    spec = link / manifest.name if position == "manifest" else manifest
    parent = (
        link if position == "parent" else link / "nested" if position == "ancestor" else tmp_path
    )
    with pytest.raises(ValueError, match="junction|Reparse|Symlink"):
        core.restore(source, spec, parent, True)
    assert not list(tmp_path.rglob("restore-rehearsal-*"))


@pytest.mark.skipif(os.name != "nt", reason="Actual native Windows symlink acceptance")
@pytest.mark.parametrize("position", ["archive", "manifest", "parent", "ancestor"])
def test_native_windows_selected_path_symlink_is_refused(tmp_path, position):
    target = tmp_path / "actual"
    target.mkdir()
    archive, manifest = selected(target)
    (target / "nested").mkdir()
    link = tmp_path / "link"
    destination = (
        archive if position == "archive" else manifest if position == "manifest" else target
    )
    try:
        link.symlink_to(destination, target_is_directory=position in {"parent", "ancestor"})
    except OSError:
        pytest.skip("Runner cannot create a real symlink; required native acceptance unavailable")
    source = link if position == "archive" else archive
    spec = link if position == "manifest" else manifest
    parent = (
        link if position == "parent" else link / "nested" if position == "ancestor" else tmp_path
    )
    with pytest.raises(ValueError, match="junction|Reparse|Symlink"):
        core.restore(source, spec, parent, True)
    assert not list(tmp_path.rglob("restore-rehearsal-*"))


@pytest.mark.parametrize("position", ["archive", "manifest", "parent", "ancestor"])
def test_portable_selected_path_symlink_is_refused(tmp_path, position):
    target = tmp_path / "actual"
    target.mkdir()
    archive, manifest = selected(target)
    (target / "nested").mkdir()
    link = tmp_path / "link"
    destination = (
        archive if position == "archive" else manifest if position == "manifest" else target
    )
    try:
        link.symlink_to(destination, target_is_directory=position in {"parent", "ancestor"})
    except OSError:
        pytest.skip("Runner cannot create real symlinks; acceptance unavailable")
    source = link if position == "archive" else archive
    spec = link if position == "manifest" else manifest
    parent = (
        link if position == "parent" else link / "nested" if position == "ancestor" else tmp_path
    )
    with pytest.raises(ValueError, match="junction|Reparse|Symlink"):
        core.restore(source, spec, parent, True)
    assert not list(tmp_path.rglob("restore-rehearsal-*"))
