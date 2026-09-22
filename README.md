# AfterMatter

> **Harness engineering, with evidence.**

AfterMatter reviews the *workflow* around an AI coding agent: it reads the agent's local
session logs plus the repository itself, and produces findings where **every claim points
back to original evidence**. Severity and scores are decided by deterministic code, fixes
are bounded, and "improved" is only claimed when longitudinal statistics support it.

**Status: pre-alpha (M0 skeleton).** No usable command yet — the repository currently
holds design documents and engineering scaffolding. A working `aftermatter analyze` is the
target of milestones M1–M2, see the plan links below.

## Where to read

| If you want | Start at |
|---|---|
| What it is, and why | [docs/PRD.md](docs/PRD.md) |
| Architecture and data contract | [docs/architecture/overview.md](docs/architecture/overview.md) |
| Build order and acceptance criteria | [docs/DEVELOPMENT-PLAN.md](docs/DEVELOPMENT-PLAN.md) |
| Full documentation map | [docs/README.md](docs/README.md) |
| How to contribute | [CONTRIBUTING.md](CONTRIBUTING.md) |

Documents under `docs/` are maintainer-facing and written in Chinese; the top-level
community files are English (ADR-0011 sets this layering).

## Non-goals

Not an LLM tracing dashboard, not a model-capability leaderboard, and not a coding agent
that performs development tasks itself.

## License

MIT — see [LICENSE](LICENSE).
