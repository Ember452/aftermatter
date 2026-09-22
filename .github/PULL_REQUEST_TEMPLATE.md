<!--
Task id from docs/DEVELOPMENT-PLAN.md goes on the first line, e.g. "Refs T1.3".
Delete this comment block before submitting.
-->

**Task / decision record:** Refs T?.? / ADR-????

## What changed

One paragraph describing the change itself.

## Why

The motivation, and why this approach rather than the alternative you rejected. Link the
evidence: failing-before/passing-after test, acceptance row in the development plan, or
the issue this closes.

## Acceptance

- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run pyright`
- [ ] `uv run pytest tests/unit -q` (plus `tests/integration` / `tests/architecture` when the change is cross-module or touches dependency direction)
- [ ] The acceptance command of the corresponding task row in `docs/DEVELOPMENT-PLAN.md` passes, and its output is pasted below or in the thread

```
paste real command output here
```

## Contracts and documents

- [ ] No contract touched, or `docs/architecture/data-model.md` was edited first and its version bumped
- [ ] A decision record exists in `docs/adr/` for dependency, contract or scope changes (AGENTS.md §2.5 triggers)
- [ ] Documentation maps kept in sync if the routing changed (`AGENTS.md` §三, `CLAUDE.md` §3, `docs/README.md`)
- [ ] `uv run python -m doc_lint --root .` passes when anything under `docs/` changed

## Privacy and honesty

- [ ] No raw session content, real absolute paths, prompts or credentials in code, tests, fixtures or this description
- [ ] Claims are limited to what was actually observed; gaps are stated as gaps
