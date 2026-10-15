# Changelog

## 0.1.0-rc.1 — 2026-10-15

- Added one explicitly selected ZIP backup plus a supplied schema-1 SHA-256 manifest. Inspect the entire selected archive and verify its file set and hashes before extraction; restore only to a random newly created disposable child under an explicitly selected parent; rehash every restored file before reporting success.
- Added original implementation, synthetic fixtures, safety regression tests, usage documentation and MIT licensing.
- Candidate only: no public release or catalog deployment is claimed.
