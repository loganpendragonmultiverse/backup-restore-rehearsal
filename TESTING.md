# Testing

Install development tools with `python -m pip install -e ".[dev]"`. Run `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, `python -m build` and `python -m pip_audit .`.

Synthetic ZIP fixtures cover verified restores, manifest mismatches, CRC corruption, file and archive size limits, expansion ratio, member counts, path depth, traversal, reserved names, collisions, encrypted or unsupported entries, symlink and reparse metadata, and refusal to use unsafe output parents. Tests never read real backups.

## Verified environments

On 2026-10-15, Linux passed 38 tests with one platform skip and 94.44% branch-aware coverage. Formatting, lint, strict typing, dependency audit and package builds passed. GitHub CI also passed on Python 3.11 across Windows, macOS and Linux. CodeQL analysis and result upload passed.

Native Windows testing passed 38 tests with one skip. `test_native_windows_junction_output_parent_is_rejected` passed: a newly created junction was refused as an output parent, and no restore directory appeared in its target. `test_selected_symlink_parent_rejected` was skipped because the account could not create an OS symlink. Linux skips the native Windows junction test by platform. Archive symlink-member rejection is tested separately.

## 0.1.1 acceptance

Run the unchanged full suite/90% branch-aware coverage gate and all documented format/lint/type/build/audit commands. Tiny real stored/deflate ZIP fixtures exercise a hidden decoded suffix, invalid deflate, incomplete end markers, trailing compressed data, exact chunk boundaries, empty files, streamed data descriptors and ZIP64 local headers. Rejected archives must create no restore target and preserve the input bytes.

The native acceptance suite `tests/test_native_paths.py` must run on actual Windows for both installed wheel and source distribution. All four junction positions and all four OS-symlink positions (archive, manifest, parent, parent ancestor) must execute without skips; run the full suite first with its original coverage gate, then this focused suite with skip/error/failure counts explicitly checked. A platform or privilege skip is unverified acceptance and blocks the native gate; no settings changes are required or authorized. Linux acceptance must also verify source/manifest/parent symlink refusal and a real verified restore for both installed distributions. Built packages must contain README, CHANGELOG, DEVELOPMENT, TESTING, LICENSE and the runnable synthetic fixture example. No actual 0.1.1 native result is claimed by this source document.

## 0.1.2 release identity checks

Release packaging compares runtime AST, project/tag version, and built wheel METADATA/source PKG-INFO Name, Version and Requires-Python before checksumming exactly two distributions. Run the packaging helper with Python 3.11+; supported application runtimes and native acceptance requirements are unchanged.
