import json
import sys
import zipfile

import pytest
from test_core import fixture

from backup_restore_rehearsal.cli import main
from backup_restore_rehearsal.core import inventory, load_manifest


def run(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["backup-restore-rehearsal", *map(str, args)])
    return main()


def test_documented_commands(monkeypatch, tmp_path, capsys):
    source, m = fixture(tmp_path)
    assert run(monkeypatch, "inspect", source, "--manifest", m) == 0
    assert json.loads(capsys.readouterr().out)["verified_files"] == 2
    assert (
        run(monkeypatch, "restore", source, "--manifest", m, "--parent", tmp_path, "--reviewed")
        == 0
    )
    assert json.loads(capsys.readouterr().out)["result"] == "verified-disposable-copy"


def test_cli_errors(monkeypatch, tmp_path):
    source, m = fixture(tmp_path)
    for args in [
        ("restore", source, "--manifest", m),
        ("restore", source, "--manifest", m, "--parent", tmp_path),
        ("inspect", tmp_path / "missing", "--manifest", m),
    ]:
        with pytest.raises(SystemExit) as error:
            run(monkeypatch, *args)
        assert error.value.code == 2


@pytest.mark.parametrize(
    "value",
    [
        [],
        {"schema": 2, "files": {}},
        {"schema": 1, "files": []},
        {"schema": 1, "files": {}},
        {"schema": 1, "files": {"x": "bad"}},
    ],
)
def test_manifest_schema_rejected(tmp_path, value):
    path = tmp_path / "m.json"
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        load_manifest(path)


def test_archive_limits_and_special_entries(tmp_path, monkeypatch):
    import backup_restore_rehearsal.core as core

    source, m = fixture(tmp_path)
    monkeypatch.setattr(core, "MAX_ARCHIVE", 1)
    with pytest.raises(ValueError, match="64 MiB"):
        core.inspect(source, m)
    monkeypatch.setattr(core, "MAX_ARCHIVE", 64 * 1024 * 1024)
    monkeypatch.setattr(core, "MAX_FILE", 2)
    with pytest.raises(ValueError, match="expansion"):
        core.inspect(source, m)


def test_encrypted_and_unsupported_metadata():
    class Fake:
        def __init__(self, entries):
            self.entries = entries

        def infolist(self):
            return self.entries

    with pytest.raises(ValueError):
        inventory(Fake([]))
    item = zipfile.ZipInfo("x")
    item.flag_bits = 1
    with pytest.raises(ValueError, match="Encrypted"):
        inventory(Fake([item]))
    item.flag_bits = 0
    item.compress_type = 99
    with pytest.raises(ValueError, match="compression"):
        inventory(Fake([item]))
    item = zipfile.ZipInfo("dir/")
    item.file_size = 1
    with pytest.raises(ValueError, match="Directory"):
        inventory(Fake([item]))


def test_mid_restore_failure_retains_only_disposable_target(tmp_path, monkeypatch):
    import backup_restore_rehearsal.core as core

    source, m = fixture(tmp_path)
    original = core.read_member

    def fail(archive, item, output=None):
        if output is not None:
            raise OSError("synthetic write failure")
        return original(archive, item, output)

    monkeypatch.setattr(core, "read_member", fail)
    with pytest.raises(ValueError, match="partial disposable target retained"):
        core.restore(source, m, tmp_path, True)
    assert len(list(tmp_path.glob("restore-rehearsal-*"))) == 1
    assert source.exists() and m.exists()
