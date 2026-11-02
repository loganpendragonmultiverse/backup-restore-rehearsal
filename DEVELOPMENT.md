# Development

Scope: One explicitly selected ZIP backup plus a supplied schema-1 SHA-256 manifest. Inspect the entire selected archive and verify its file set and hashes before extraction; restore only to a random newly created disposable child under an explicitly selected parent; rehash every restored file before reporting success.

The tool has no discovery, scheduler, network or credential integration. No real backup is accessed without an explicit archive argument. Only selected archive/manifest files and generated disposable targets are touched. Never pass live backup directories, production destinations or sensitive files to issue reports. Failure after target creation retains the partial disposable directory for inspection; no cleanup deletes user data.

ZIP stored/deflate only. No tar, 7z, RAR, encrypted archives, disk images, application-aware recovery, metadata/permissions restoration, or automatic backup discovery. Limits: 64 MiB compressed archive and total expanded bytes, 16 MiB per file, 2,000 entries, depth 16 and expansion ratio 100. All symlinks, junctions, reparse points and special members are rejected, including links within the target; this deliberately excludes some legitimate backups. This is a rehearsal, not a production recovery utility or proof that an application can open the restored data. Select a trusted local parent not writable by other accounts; this MVP does not defend against a hostile process running as the same user concurrently replacing directories or mutating files.

Install editable development dependencies with `python -m pip install -e ".[dev]"`. Run `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, `python -m build` and `python -m pip_audit .`. Runtime dependencies are empty.

## Release process

Use a branch and pull request for changes. Run the test matrix and CodeQL, resolve review conversations, and let the maintainer make the final merge decision. CI workflows use read-only permissions and pinned actions.

For a release, keep the package version and changelog in agreement, create an annotated semantic-version tag, and use that tag's successful release build. Verify the downloadable files against SHA256SUMS before publishing a GitHub release. Never bypass repository protections or publish artifacts from a different commit.

## 0.1.1 complete-stream verification

Inspection checks the complete declared compressed span as well as the ZIP reader's logical file bytes. Stored members must have an exact decoded length; deflate members must reach their end marker without hidden decoded suffixes or trailing compressed bytes. Size, CRC-32 and supplied SHA-256 must all agree before creating a restore target. Processing remains chunk-bounded (at most 64 KiB of decoded output per validation step, including a possible one-byte over-limit probe); the existing archive/file/total/count/depth/ratio limits remain unchanged. Standard data descriptors and ZIP64 local headers remain supported within those limits. Malformed deflate input produces a controlled CLI error. Schema versions are integers and direct API restore acceptance must be boolean true. This does not add protection against concurrent hostile mutation by the same user.

## 0.1.2 release identity checks

Release packaging compares runtime AST, project/tag version, and built wheel METADATA/source PKG-INFO Name, Version and Requires-Python before checksumming exactly two distributions. Run the packaging helper with Python 3.11+; supported application runtimes and native acceptance requirements are unchanged.
