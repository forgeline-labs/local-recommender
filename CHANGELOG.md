# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-16

### Added

- Public library function `local_recommender.recommend(interactions, user,
  limit=5)` implementing deterministic item-item collaborative filtering with
  binary cosine similarity.
- CLI entrypoints `app` (POSIX, executable) and `app.cmd` (Windows), plus
  `python app` on both platforms:
  - `python app recommend FILE --user USER [--limit N]`
  - `python app --version` → `local-recommender 0.1.0`
  - `python app --help`
- Strict validation for identifiers, schema, limits, JSON syntax, duplicate
  keys and non-finite numbers; exit codes `2` for validation and `3` for I/O.
- Public black-box test suite in `tests/`, traced to acceptance criteria
  AC-1 through AC-12.
- CI workflow running lint and tests on Ubuntu and Windows with Python 3.12.
- Documentation: README, this changelog, MIT licence and per-run record.

### Notes

- No runtime dependencies; standard library only.
- No persistence, server, network access or accounts.

[0.1.0]: https://example.invalid/local-recommender/releases/tag/v0.1.0
