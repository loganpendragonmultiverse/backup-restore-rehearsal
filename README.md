# Backup Restore Rehearsal

Rehearse a user-selected ZIP restore into a new disposable, manifest-verified target.

Current status: **v0.1.0-rc.1 — review candidate, not a public release**. Original implementation for Logan Pendragon Forge. MIT licensed. No paid services, account or credentials are needed.

## Three-minute start

```sh
python -m pip install .
python examples/make_fixture.py
backup-restore-rehearsal inspect synthetic.zip --manifest synthetic-manifest.json
# Review the inspection result, then choose an existing private output parent.
backup-restore-rehearsal restore synthetic.zip --manifest synthetic-manifest.json --parent . --reviewed
```

## What this candidate does

One explicitly selected ZIP backup plus a supplied schema-1 SHA-256 manifest. Inspect the entire selected archive and verify its file set and hashes before extraction; restore only to a random newly created disposable child under an explicitly selected parent; rehash every restored file before reporting success.

## Privacy and safe operation

The tool has no discovery, scheduler, network or credential integration. No real backup is accessed without an explicit archive argument. Only selected archive/manifest files and generated disposable targets are touched. Never pass live backup directories, production destinations or sensitive files to issue reports. Failure after target creation retains the partial disposable directory for inspection; no cleanup deletes user data.

## Boundaries

ZIP stored/deflate only. No tar, 7z, RAR, encrypted archives, disk images, application-aware recovery, metadata/permissions restoration, or automatic backup discovery. Limits: 64 MiB compressed archive and total expanded bytes, 16 MiB per file, 2,000 entries, depth 16 and expansion ratio 100. All symlinks, junctions, reparse points and special members are rejected, including links within the target; this deliberately excludes some legitimate backups. This is a rehearsal, not a production recovery utility or proof that an application can open the restored data. Select a trusted local parent not writable by other accounts; this MVP does not defend against a hostile process running as the same user concurrently replacing directories or mutating files.

## Development and support

Requires Python 3.11+; the runtime has no third-party dependencies. Windows and Linux acceptance results are recorded in TESTING.md; macOS remains a CI gate. See [DEVELOPMENT.md](DEVELOPMENT.md), [TESTING.md](TESTING.md), [SECURITY.md](SECURITY.md), and [CHANGELOG.md](CHANGELOG.md). Pull requests receive maintainer review; no contribution or release merges automatically. Maintenance is on demand, with no service-level commitment.
