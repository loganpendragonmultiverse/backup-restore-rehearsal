# Changelog

## 0.1.2 — 2026-10-21

- Verify built distribution Name, Version and Requires-Python against project, runtime and tag identity before writing exact two-payload checksums.
- Add portable metadata mismatch, duplicate and missing-field, runtime, tag and payload-set regressions without changing native requirements or supported runtimes.

## 0.1.1 — 2026-10-21

- Verify complete bounded stored/deflate streams, including decoded length, deflate end marker, absence of hidden suffix/tail bytes and CRC, before accepting manifest hashes or creating a restore target.
- Return controlled malformed-deflate errors, require integer manifest versions and explicit boolean API review acceptance.
- Preserve ZIP data descriptors, ZIP64 local headers, original limits and partial-target retention. Add real malformed-stream and native filesystem regressions.
- Include all operating documents, license and synthetic fixture example in installed wheels as well as source distributions.

## 0.1.0 — 2026-10-15

- Added one explicitly selected ZIP backup plus a supplied schema-1 SHA-256 manifest. Inspect the entire selected archive and verify its file set and hashes before extraction; restore only to a random newly created disposable child under an explicitly selected parent; rehash every restored file before reporting success.
- Add CRC-corruption, inclusive size/count boundaries, reparse-attribute and native Windows junction regression fixtures.
- Added synthetic examples, regression tests, usage documentation and MIT licensing.
- Added version-checked release packaging with SHA-256 checksums.
