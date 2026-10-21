# Backup Restore Rehearsal

Rehearse a user-selected ZIP restore into a new disposable, manifest-verified target.

MIT licensed. Runs locally without an account or external service. See [GitHub Releases](https://github.com/loganpendragonmultiverse/backup-restore-rehearsal/releases) for downloads.

## Three-minute start

```sh
python -m pip install .
python examples/make_fixture.py
backup-restore-rehearsal inspect synthetic.zip --manifest synthetic-manifest.json
# Review the inspection result, then choose an existing private output parent.
backup-restore-rehearsal restore synthetic.zip --manifest synthetic-manifest.json --parent . --reviewed
```

## Features

One explicitly selected ZIP backup plus a supplied schema-1 SHA-256 manifest. Inspect the entire selected archive and verify its file set and hashes before extraction; restore only to a random newly created disposable child under an explicitly selected parent; rehash every restored file before reporting success.

## Privacy and safe operation

The tool has no discovery, scheduler, network or credential integration. No real backup is accessed without an explicit archive argument. Only selected archive/manifest files and generated disposable targets are touched. Never pass live backup directories, production destinations or sensitive files to issue reports. Failure after target creation retains the partial disposable directory for inspection; no cleanup deletes user data.

## Boundaries

ZIP stored/deflate only. No tar, 7z, RAR, encrypted archives, disk images, application-aware recovery, metadata/permissions restoration, or automatic backup discovery. Limits: 64 MiB compressed archive and total expanded bytes, 16 MiB per file, 2,000 entries, depth 16 and expansion ratio 100. All symlinks, junctions, reparse points and special members are rejected, including links within the target; this deliberately excludes some legitimate backups. This is a rehearsal, not a production recovery utility or proof that an application can open the restored data. Select a trusted local parent not writable by other accounts; this MVP does not defend against a hostile process running as the same user concurrently replacing directories or mutating files.

## Development and support

Requires Python 3.11+; the runtime has no third-party dependencies. Historical acceptance results and the current native acceptance requirements are recorded in TESTING.md. Releases require the Windows, macOS and Linux CI matrices and installed-artifact gates. See [DEVELOPMENT.md](DEVELOPMENT.md), [TESTING.md](TESTING.md), [SECURITY.md](SECURITY.md), and [CHANGELOG.md](CHANGELOG.md). Pull requests receive maintainer review; no contribution or release merges automatically. Maintenance is on demand, with no service-level commitment.

## 0.1.1 complete-stream verification

Inspection checks the complete declared compressed span as well as the ZIP reader's logical file bytes. Stored members must have an exact decoded length; deflate members must reach their end marker without hidden decoded suffixes or trailing compressed bytes. Size, CRC-32 and supplied SHA-256 must all agree before creating a restore target. Processing remains chunk-bounded (at most 64 KiB of decoded output per validation step, including a possible one-byte over-limit probe); the existing archive/file/total/count/depth/ratio limits remain unchanged. Standard data descriptors and ZIP64 local headers remain supported within those limits. Malformed deflate input produces a controlled CLI error. Schema versions are integers and direct API restore acceptance must be boolean true. This does not add protection against concurrent hostile mutation by the same user.
