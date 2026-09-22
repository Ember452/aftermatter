# Changelog

All notable changes to AfterMatter are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), the project adheres to Semantic
Versioning, and milestone releases are tagged as `v0.N.0-<milestone>` (ADR-0006).

## [Unreleased]

### Added

- M0 engineering skeleton: `src/aftermatter` package with a single-source version, full
  toolchain configuration in `pyproject.toml` (ruff / pyright / pytest / hatchling),
  dependency-direction guard tests under `tests/architecture/`, a three-platform CI
  matrix, and the community files (README / LICENSE / CONTRIBUTING / SECURITY).
- `scripts/doc_lint/` documentation consistency checker plus its `docs.yml` gate
  (delivered during the documentation baseline phase).

### Changed

- No behaviour changes yet: there is no public command and no released functionality.
