# Changelog

All notable changes to this project will be documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2025-04-01

### Added
- Initial release.
- `SDFParser.read()` — parse single `.sdf` files or directories.
- `SDFParser.reset()` — clear state for parser reuse.
- Support for `IOPATH`, `COND`, `CONDELSE`, `WIDTH`, `SETUPHOLD`, `RECREM`.
- Cross-file cell consistency check with diff warning when parsing directories.
- Single-cell extraction mode via `given_cell` argument.
- `format_entries()` utility for human-readable output.
- CLI via `sdf-parser` / `python -m sdf_parser`.
- Optional colored warnings with `termcolor` (graceful fallback if not installed).
- MIT license.
