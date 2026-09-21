# CLAUDE.md — AfterMatter Development Guidelines

> **Mirror notice:** this file is the English mirror of [AGENTS.md](AGENTS.md).
> AGENTS.md is canonical; when you change rules in either file, update the other
> in the same commit. Content below must stay semantically identical.

Behavioral guidelines and project constraints for AI-assisted development.
Merge with per-task instructions; this file wins on conflict.

**Tradeoff:** these rules bias toward caution over speed. For trivial tasks
(typo fixes, one-line logs) use judgment; when unsure, follow the rules.

---

## 1. Project Positioning (align at the start of every session)

**What AfterMatter is**: evidence-based review of AI coding agent workflows —
it reads local coding-agent sessions (Claude Code / Codex / Cursor / Qoder) plus
repository evidence, scores the five dimensions of the Agent Work Loop, and
produces findings where "every claim traces back to raw bytes", closing the loop
with bounded repairs and longitudinal statistical validation.

**What it is NOT** (scope-drift guards, checked in review):
- ❌ LLM tracing / observability dashboards (red ocean, deliberately abandoned)
- ❌ A coding agent framework itself (we review; we do not execute dev tasks)
- ❌ Model capability leaderboards

**Three product-level iron laws** (no implementation may violate them):
1. Honest presentation: no claim without evidence; evidence gaps are marked
   `Unobserved` explicitly — never an invented score.
2. Models propose, tools decide: LLM output is candidates only; severity, scores
   and state transitions are decided by deterministic code.
3. Dual brains, one contract: Brain 1 (host-parasitic) and Brain 2 (built-in
   engine) consume the same EvidenceBundle and emit the same Finding schema —
   the contract never forks for implementation convenience.

Naming: brand display form is **AfterMatter**; every technical identifier is
lowercase **aftermatter** (package / import / CLI / directories).

## 2. Behavioral Guidelines

### 2.1 Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

- State assumptions before implementing; ask when uncertain.
- If multiple interpretations exist, lay them out — never pick silently.
- Speak up when a simpler approach exists; push back when warranted.
- When something is unclear, stop, name the confusion, ask.
- Contract-level changes (data model, state machine, message protocol):
  **edit the docs first, code follows** — never the other way around.

### 2.2 Simplicity First

Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked; no abstractions for single-use code.
- No unrequested "flexibility/configurability"; no error handling for
  impossible scenarios.
- If 200 lines could be 50, rewrite.
- Ask yourself: "Would a senior engineer call this overcomplicated?" If yes, simplify.

### 2.3 Surgical Changes

Touch only what you must. Clean up only your own mess.

- Don't "improve" adjacent code, comments or formatting; don't refactor what works.
- Match existing style even if you'd do it differently; report unrelated dead
  code — don't delete it.
- Remove imports/variables your change orphaned; leave pre-existing dead code alone.
- File layout inside a directory is the implementer's choice, but **no catch-all
  `utils/`, `common/`, `helpers/` directories** (`core/` holds only the five
  genuine basics: time / hashing / paths / logging / errors).
- The test: **every changed line traces to a task id (T-x.x) or a user instruction.**

### 2.4 Goal-Driven Execution

Define success criteria. Loop until verified.

- "Add validation" → write tests for invalid input first, then make them pass.
  "Fix a bug" → write a reproducing test first, then fix.
- For multi-step tasks, state the plan: `1. [step] → verify: [check]`.
- Self-certify each task against the acceptance column in
  `docs/aftermatter-开发计划.md` chapter 3 — **"seems to work" is not evidence**.

### 2.5 Decision Capture — record key decisions before acting

**Triggers** (any hit requires a written decision record before implementation):

1. Changing data contracts / state machine / message protocols (the
   "edit data-model.md first" rule applies too: the ADR records *why*,
   data-model.md records *what changed*)
2. Technology or dependency selection changes (incl. overview.md §5 table)
3. Scope cuts or changes (invoking development-plan §3 cut lists, PRD edits)
4. Implementation contradicts docs and a judgment call is needed
5. Discovering inconsistency between documents (resolution must be written
   back to both files)

**Rules**: write a one-pager in `docs/adr/` (`NNNN-title.md`, template in its
README) before acting; if it exceeds one page, promote to `docs/specs/`
(date-prefixed). The corresponding commit footer must carry `Refs ADR-NNNN`.
**Unrecorded changes of this kind are rejected outright in review.** Historical
decisions: `docs/adr/0001–0008` and `docs/specs/`.

## 3. Documentation Map (route by task; never modify core modules unread)

| To do | Read first (in order) |
|-------|----------------------|
| Any task before starting | `docs/aftermatter-开发计划.md` (its task row + ch.1 protocol) |
| Data model / state machine | `docs/architecture/data-model.md` (contract source) → edit doc, bump version |
| Collectors / adapters | `docs/architecture/collectors.md` → `modules.md` §2 → `data-model.md` §1 → fixtures |
| Analysis engine / multi-agent | `docs/architecture/analysis.md` → `overview.md` §1/§6 → `modules.md` §5 |
| Repair / sandbox / longitudinal | `docs/architecture/repair.md` / `sandbox.md` / `longitudinal.md` → `overview.md` §4.2 |
| Other modules | Same-named internal design doc; full list in `docs/architecture/INDEX.md` |
| Fits nowhere above | Write a lightweight ADR in `docs/adr/` first, then act |

Global entry: `docs/README.md` (seven-stage reading map). Hard dependency rules:
`docs/architecture/overview.md` §3, enforced by `tests/architecture/`.

## 4. Code Quality Constraints

### 4.1 Quality gates (Definition of Done, every task)

```bash
uv run ruff check .            # lint: E,F,I,UP,B,SIM (config in pyproject.toml)
uv run ruff format --check .   # formatting: ruff-format (black-compatible)
uv run pyright                 # types: zero errors on public API; no new type: ignore
uv run pytest tests/unit -q    # tests: this task green + full unit suite unregressed
```

Contract/integration changes also run `uv run pytest tests/integration -q`;
import-direction / model-immutability changes also `uv run pytest tests/architecture -q`.
**pre-commit hooks and CI run the same commands; local green ≠ skipping.**

### 4.2 Coding discipline

- **Types**: annotations on all public APIs; pydantic v2 models for all
  cross-boundary data — never raw dicts.
- **Async**: no blocking calls in the event loop (sync IO, `time.sleep`, sync
  requests); every IO has a timeout; `asyncio.CancelledError` must propagate.
- **Errors**: catch only expected, specific exceptions (classify via the
  `AfterMatterError` tree in `core`); no bare try/except; reuse the providers
  layer's LLM error taxonomy instead of re-classifying in business code.
- **Logging**: `logging`, never `print`; structured fields carry `trace_id`;
  log what happened plus key parameters, not emotions.
- **Comments**: only the "why" the code can't say (constraints, tradeoffs,
  pitfalls); never restate what the code does.
- **Tests**: new features ship with tests; fixtures and labels **before**
  implementation (adapters / classifiers / statistics especially); fake out
  LLM/network/FS entirely; pytest-asyncio auto mode.
- **Dependencies**: check pyproject and the overview.md §5 table before adding
  one; **a new dependency requires an ADR in docs/adr/ plus justification in
  the commit body.**

### 4.3 Project-specific red lines

1. **No LLM-calling code before M2 completes** (development-plan iron law).
2. **`tests/adversarial/` only ever grows**; making an adversarial case pass by
   editing the case itself counts as cheating.
3. `replay_ok` is written only by the sandbox (single entry point); `severity`
   only by the Lead; `verified/regressed` only by the state-machine driver —
   **bypass writes = contract breach, rejected on sight**.
4. Raw sessions, full prompts and real paths **never** leave the machine and
   never enter test fixtures.
5. data-model.md + `schemas/` are the single source of truth for contracts;
   other documents reference, never restate.

## 5. Git and Commit Rules

**Never `git commit` or `git push` without the user's explicit permission.**
After a stage task (T-x.x / milestone) completes: report the change list and
test results → **ask** whether to commit/tag → act only on instruction.

Commit messages are **English Conventional Commits** (international OSS project):

```
<type>(<scope>): <imperative, lowercase, no period, ≤72 chars>

[optional body: what changed + WHY, wrapped at 72]
[optional footer: Refs T-x.x / ADR-NNNN]
```

- type: `feat` / `fix` / `refactor` / `test` / `docs` / `chore` / `perf`
- scope: module directory names (`collectors`, `episodes`, `evidence`,
  `analysis`, `repair`, `longitudinal`, `report`, `serve`, `daemon`, `cli`,
  `ci`, `docs`)
- **Granularity**: one commit = one logical change = independently revertible.
  Implementation and its tests share a commit
  (`feat(collectors): add claude adapter with fixture coverage`); no giant
  multi-module batches, no per-save fragmentation.
- "Why it changed" beats "which file it touched"; body states impact and task id.
- Tags at milestone exit: `v0.N.0-<milestone>` (e.g. `v0.1.0-m0-skeleton`,
  `v0.2.0-m1-evidence-kernel`; sequence per ADR-0006). Tagging also requires asking.

Good / bad example:

```
# good: scoped, motivated, revertible
fix(episodes): split episodes on new-task prompt even within gap window

Prompt-only continuations were merging unrelated goals into one episode,
breaking acceptance-boundary claims in Change Validation.
Refs T1.7

# bad: giant / vague
update stuff
```

## 6. End-of-Session Self-Check

Before reporting any task done, confirm each item:

- [ ] All four DoD commands actually ran green (paste output, don't paraphrase)
- [ ] Every changed line traces to a task id or user instruction; no drive-by edits
- [ ] Contract changes: docs edited first, versions bumped
- [ ] No new print / bare except / IO without timeout / unannotated public API
- [ ] Orphans from my own change cleaned up; unrelated dead code reported, not deleted
- [ ] Next-step suggestion stated clearly; **never start the next task unasked**

These guidelines are working if: fewer unnecessary changes in diffs, fewer
rewrites due to overcomplication, and clarifying questions come before
implementation rather than after mistakes.
