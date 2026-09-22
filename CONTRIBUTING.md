# Contributing

AfterMatter is evidence-driven: a claim belongs in a report only when it points back to
original bytes, and a task is "done" only when its acceptance command passes. The same
honesty applies to contributions.

## Environment

```bash
uv sync              # creates .venv and installs the dev group
uv run pytest -q     # sanity check
```

Python >= 3.12 is required; CI covers 3.12 and 3.13 on Linux, Windows and macOS.

## Definition of done

Every change must pass these four commands, and they are the same commands CI runs:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest tests/unit -q
```

Add the following when the change touches more than one module:

- `uv run pytest tests/integration -q` for cross-module flows;
- `uv run pytest tests/architecture -q` for import direction or model immutability;
- `uv run python -m doc_lint --root .` when anything under `docs/` changed.

`pre-commit` is run with `uvx pre-commit run --all-files` (it is deliberately not a
declared dependency, see ADR-0012).

## Where code goes

Directory ownership and the dependency-direction rules are normative:

- repository layout: `docs/REPO-LAYOUT.md`;
- layering rules (enforced by `tests/architecture/test_import_direction.py`):
  `docs/architecture/overview.md` section 3;
- module contracts: `docs/architecture/modules.md`.

If your change does not fit anywhere in those documents, open a discussion before writing
it — do not create a new top-level package on the side.

## Commits and pull requests

Conventional Commits in English: `<type>(<scope>): <imperative summary>`, then a body that
explains **why** and references the task id (`Refs T1.3`) or decision record
(`Refs ADR-0012`). One logical change per commit; implementation and its tests belong in
the same commit.

Branch from `main`, keep the branch short-lived, and link the task id from
`docs/DEVELOPMENT-PLAN.md` in the PR description. The acceptance column of that plan is
the review criterion, not "it looks like it works".

## Decision records

Write a one-page record in `docs/adr/` **before** implementing anything that changes a data
contract, state machine, message protocol, dependency choice, or scope. Contract documents
(`docs/architecture/data-model.md`) are edited first and their version bumped; code follows
the document, never the other way round.

## Language

The two README files form a bilingual front door: `README.md` is Chinese (default landing) and
`README.en.md` is its English mirror - they must carry the same structure and the same facts, so a
PR touching one is expected to touch the other (ADR-0015). The remaining community-facing files
(`CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`) and `docs/development/`, `docs/api/` are English;
maintainer-facing design documents under `docs/` are Chinese (ADR-0011). Identifiers and commit
messages are always English; code comments follow the style of the file you are editing, which in
this repository's internal code means Chinese comments that explain *why*, not code that restates
*what* it does.
