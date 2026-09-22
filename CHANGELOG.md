# Changelog

All notable changes to AfterMatter are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), the project adheres to Semantic
Versioning, and milestone releases are tagged as `v0.N.0-<milestone>` (ADR-0006).

## [Unreleased]

Nothing runnable yet. The next milestone is M1 (deterministic evidence kernel), which is where
first-party functionality - not scaffolding - starts to accumulate.

### Added

- Bilingual front door: `README.md` is now the Chinese landing page with `README.en.md` as its
  English mirror, plus brand assets under `docs/assets/` (ADR-0015).
- `docs/reports/` for milestone closing reports with a fixed skeleton, seeded by the M0 report
  (ADR-0014).
- Decision indexes in `docs/adr/README.md` and `docs/specs/README.md`.

### Changed

- `docs/tests/` became the repository's only Chinese-filename exemption, enforced by
  `policy_checker` (ADR-0013).
- Acceptance commands in the development plan no longer rely on `&&`, which PowerShell cannot run.
- External evidence anchors now use tag names and workflow run numbers instead of commit sha, after
  a `git filter-branch` history rewrite made older sha unreachable.

## [0.1.0] - 2026-09-22 — tag `v0.1.0-m0-skeleton`

Pre-alpha engineering milestone: there is **no command and no published artifact**. The tag
marks a verified milestone boundary, not a usable release.

### Added

- M0 engineering skeleton: `src/aftermatter` package with a single-source version, full
  toolchain configuration in `pyproject.toml` (ruff / pyright / pytest / hatchling),
  dependency-direction guard tests under `tests/architecture/`, a three-platform CI
  matrix (3.12/3.13 × ubuntu/windows/macos), dependabot and issue/PR templates, and the
  community files (README / LICENSE / CONTRIBUTING / SECURITY / these notes).
- `scripts/doc_lint/` documentation consistency checker plus its `docs.yml` gate
  (delivered during the documentation baseline phase).

### Changed

- `scripts/doc_lint/` was brought under the new lint and format gate; purely cosmetic,
  the checker reports the same zero violations as before.

[Unreleased]: https://github.com/Ember452/aftermatter/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Ember452/aftermatter/releases/tag/v0.1.0
