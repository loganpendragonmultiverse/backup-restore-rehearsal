# Development handoff

Approved scope: One explicitly selected ZIP backup plus a supplied schema-1 SHA-256 manifest. Inspect the entire selected archive and verify its file set and hashes before extraction; restore only to a random newly created disposable child under an explicitly selected parent; rehash every restored file before reporting success.

The tool has no discovery, scheduler, network or credential integration. No real backup is accessed without an explicit archive argument. Only selected archive/manifest files and generated disposable targets are touched. Never pass live backup directories, production destinations or sensitive files to issue reports. Failure after target creation retains the partial disposable directory for inspection; no cleanup deletes user data.

ZIP stored/deflate only. No tar, 7z, RAR, encrypted archives, disk images, application-aware recovery, metadata/permissions restoration, or automatic backup discovery. Limits: 64 MiB compressed archive and total expanded bytes, 16 MiB per file, 2,000 entries, depth 16 and expansion ratio 100. All symlinks, junctions, reparse points and special members are rejected, including links within the target; this deliberately excludes some legitimate backups. This is a rehearsal, not a production recovery utility or proof that an application can open the restored data. Select a trusted local parent not writable by other accounts; this MVP does not defend against a hostile process running as the same user concurrently replacing directories or mutating files.

Repository target: `loganpendragonmultiverse/backup-restore-rehearsal`. Candidate version: `v0.1.0-rc.1` (PEP 440: 0.1.0rc1). Source must remain independent of all existing portfolio implementations. Shared community files and pinned CI conventions follow the canonical portfolio.

Install editable development dependencies with `python -m pip install -e ".[dev]"`. Run `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, `python -m build` and `python -m pip_audit .`. Runtime dependencies are empty.

## Publication gate

This candidate does not authorize bypassing protected branches, failed checks or security review. Before a public release: review scope and source; run CI and CodeQL; configure protected main and required checks, squash-only merges, resolved conversations, read-only workflow permissions, security reporting, scanning and dependency alerts; obtain maintainer release review; build from the reviewed annotated tag; verify downloadable SHA-256 values; publish exact approved source/artifacts. Enable Pages for the keyboard app after browser acceptance. Parent task owns catalog coordination: update release register, catalog, generated information pages and sitemap only after verified GitHub release evidence, then render/deploy/live-verify and reconcile the Open Source Engine. Reconcile/audit organization all-activity watches. Do not advertise candidate versions as released.
